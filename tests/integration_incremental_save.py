"""Manual Mac integration test. Requires a running Apple container service and
`container image pull --platform linux/arm64 python:3.12-alpine`.
Creates only uniquely named test containers/images and removes them afterwards.
"""
import importlib.util,json,copy,hashlib,tarfile,gzip,io,tempfile,subprocess,time,shutil,uuid
from pathlib import Path
project=Path(__file__).resolve().parents[1]
def module(name,file):
 s=importlib.util.spec_from_file_location(name,project/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
c=module('control','scripts/container-control.py'); inc=module('inc','scripts/incremental_save.py')
root=Path(tempfile.mkdtemp(prefix='project-incremental-integration-')).resolve();state=root/'state';state.mkdir()
cli=shutil.which('container');assert cli,'Apple container is required';prefix='project-delta-'+uuid.uuid4().hex[:8]
base=prefix+':base';one=prefix+':one';two=prefix+':two';name=prefix+'-source';restored=prefix+'-restore'
images=[];containers=[]
def run(*args):return c.run(cli,*args)
def load_fixture():
 _,manifest,config=inc.manifest_for(cli,'python:3.12-alpine',c.run)
 r=root/'fixture';(r/'blobs/sha256').mkdir(parents=True)
 stream=io.BytesIO()
 with tarfile.open(fileobj=stream,mode='w',format=tarfile.PAX_FORMAT) as t:
  for n,data in [('probe/unchanged.bin',b'u'*2000000),('probe/delete',b'delete'),('probe/directory/child',b'old'),('probe/type',b'file')]:
   h=tarfile.TarInfo(n);h.size=len(data);h.mode=0o644;h.mtime=1234567890;t.addfile(h,io.BytesIO(data))
 data=stream.getvalue();compressed=gzip.compress(data,mtime=0)
 digest=hashlib.sha256(compressed).hexdigest();(r/'blobs/sha256'/digest).write_bytes(compressed)
 config['rootfs']['diff_ids'].append('sha256:'+hashlib.sha256(data).hexdigest());config.setdefault('history',[]).append({'created_by':'fixture'})
 manifest['config']=c.blob(r,config,'application/vnd.oci.image.config.v1+json');manifest['layers'].append({'digest':'sha256:'+digest,'size':len(compressed),'mediaType':'application/vnd.oci.image.layer.v1.tar+gzip'})
 desc=c.blob(r,manifest,'application/vnd.oci.image.manifest.v1+json');desc['platform']={'os':'linux','architecture':'arm64'};desc['annotations']={'io.containerd.image.name':base,'com.apple.containerization.image.name':base,'org.opencontainers.image.ref.name':'base'}
 c.atomic_json(r/'index.json',{'schemaVersion':2,'manifests':[desc]});c.atomic_json(r/'oci-layout',{'imageLayoutVersion':'1.0.0'})
 archive=root/'fixture.tar'
 with tarfile.open(archive,'w') as t:
  for p in r.rglob('*'):
   if p.is_file():t.add(p,arcname=str(p.relative_to(r)))
 inc.native_import(archive,state,c.run);images.append(base)
 print('Native import without rootfs unpack: PASS',flush=True)
try:
 load_fixture()
 ident=c.channel_id(name);channel=state/'channels'/ident;channel.mkdir(parents=True)
 c.atomic_json(state/'registry.json',{ident:{'container':name,'base_image':base}})
 run('run','-d','--name',name,'--mount','type=bind,source='+str(channel)+',target=/run/project-container-control','--entrypoint','/bin/sleep',base,'600');containers.append(name)
 run('exec','--user','root',name,'python3','-c',"from pathlib import Path;import os,shutil;p=Path('/probe');(p/'delete').unlink();shutil.rmtree(p/'directory');(p/'directory').symlink_to('new');(p/'type').unlink();(p/'type').mkdir();(p/'type'/'child').write_text('child');(p/'new').write_text('first');os.chmod(p/'new',0o751);os.link(p/'new',p/'hard');os.setxattr(p/'new','user.project-test',b'preserved')")
 stamp=time.monotonic();result=c.save_image(cli,name,one,state/'backups'/ident/'one');images.append(one)
 print('First incremental Save:',time.monotonic()-stamp,result,flush=True)
 assert result['delta_bytes']<1000000,result
 run('run','-d','--name',restored,'--entrypoint','/bin/sleep',one,'600');containers.append(restored)
 run('exec',restored,'python3','-c',"from pathlib import Path;import os;p=Path('/probe');assert not (p/'delete').exists();assert (p/'directory').is_symlink();assert (p/'type'/'child').read_text()=='child';assert (p/'new').read_text()=='first';assert (p/'new').stat().st_mode&0o777==0o751;assert (p/'new').stat().st_ino==(p/'hard').stat().st_ino;assert os.getxattr(p/'new','user.project-test')==b'preserved';assert (p/'unchanged.bin').stat().st_size==2000000")
 print('Restore content, deletions, type changes, permissions, hardlinks, xattrs: PASS',flush=True)
 run('stop',restored);run('delete',restored);containers.remove(restored)
 c.update_registry(state,lambda r:r[ident].update(saved_image=one,last_save=result))
 run('exec',name,'python3','-c',"from pathlib import Path;p=Path('/probe');(p/'second').write_text('second')")
 stamp=time.monotonic();result2=c.save_image(cli,name,two,state/'backups'/ident/'two');images.append(two)
 print('Second incremental Save:',time.monotonic()-stamp,result2,flush=True)
 assert result2['parent_image']==one;assert result2['delta_bytes']<10000
 _,m1,_=inc.manifest_for(cli,one,c.run);_,m2,_=inc.manifest_for(cli,two,c.run);assert m2['layers'][:-1]==m1['layers']
 with tarfile.open(result2['archive']) as t:
  layer=[m for m in t.getmembers() if m.name=='blobs/sha256/'+m2['layers'][-1]['digest'][7:]][0]
  with tarfile.open(fileobj=io.BytesIO(gzip.decompress(t.extractfile(layer).read()))) as delta:
   assert 'probe/second' in delta.getnames();assert 'probe/unchanged.bin' not in delta.getnames();assert 'probe/new' not in delta.getnames()
 print('Repeated Save reuses previous layers and excludes unchanged data: PASS',flush=True)
 run('run','-d','--name',restored,'--entrypoint','/bin/sleep',two,'600');containers.append(restored)
 run('exec',restored,'python3','-c',"from pathlib import Path;p=Path('/probe');assert (p/'second').read_text()=='second';assert (p/'new').read_text()=='first';assert not (p/'delete').exists()")
 print('Second restore: PASS',flush=True)
finally:
 for item in containers:
  subprocess.run([cli,'stop',item],capture_output=True);subprocess.run([cli,'delete',item],capture_output=True)
 for item in reversed(images): subprocess.run([cli,'image','delete',item],capture_output=True)
 print('Test artifacts:',root,flush=True)
