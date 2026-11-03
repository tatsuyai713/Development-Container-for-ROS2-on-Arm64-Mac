# Development-Container-for-ROS2-on-Arm64-Mac

[English guide](README.md)

Apple SiliconのMacで、UbuntuのデスクトップとROS 2の開発環境を使うためのプロジェクトです。
ブラウザまたはRDPクライアントから接続し、Linux用のアプリや開発ツールを操作できます。
Apple公式の`container`を使うため、この手順にDocker Desktopは必要ありません。

初めての方は、**セットアップ → イメージ作成 → 起動 → ブラウザまたはRDPで接続 → アプリで作業 → 停止**の順に進めます。
以下の前半は利用手順です。内部の仕組みを理解しなくても使えるよう、技術説明は最後にまとめています。

### この環境でできること

| やりたいこと | 使い方 |
|---|---|
| Ubuntuの画面をMacで操作する | MacのChrome・SafariでHTTPSのURLを開く、またはRDPクライアントで接続する |
| ROS 2を学習・開発する | Ubuntu内のKonsoleでROS 2を読み込み、ノードの実行やパッケージのビルドを行う |
| Linux用アプリを使う | Ubuntu内のChromeを起動。開発ツールを有効にすればLibreOfficeやエディターも使える |
| Macのソースコードや文書を使う | ホーム共有を有効にし、Ubuntuの`~/host_home`から開く |
| 作業環境を残して終了する | Desktopの**Stop Container**で停止し、次回Macから起動する |
| 追加したアプリも含めて環境を保存する | Desktopの**Save Container Image**で保存し、必要になったときに再作成する |

### どの方法でデスクトップを開くか

| 接続方法 | Macで開くもの | 接続先の例（UID 501・既定ポート） |
|---|---|---|
| [ブラウザ接続](#browser) | Google ChromeまたはSafari | `https://127.0.0.1:60501` |
| [RDP接続](#rdp) | RDPクライアント | `127.0.0.1:3389` |

ブラウザではSelkiesの画面を開きます。RDPクライアントのインストールは不要です。
RDPを選ぶ場合は、起動設定でXRDPを有効にします。両者は別のデスクトップセッションです。
接続先の番号は設定によって変わるため、下の手順で自分の値を確認してください。
すでにセットアップ済みの方は「毎日の起動と終了」から再開できます。

- [初回セットアップ](#setup)
- [デスクトップに接続する](#connect)：[ブラウザ](#browser) / [RDP](#rdp) / [コピー＆ペースト](#clipboard)
- [デスクトップのアイコンを使う](#desktop)
- [毎日の起動と終了](#daily)
- [ファイルを保存する・Macと共有する](#files)
- [ROS 2やアプリを使う](#usage)
- [環境を保存・復元・更新する](#save)
- [困ったとき](#troubleshooting)
- [コマンド一覧と複数環境](#commands)
- [技術的な仕組みと制約](#technical)

<a id="setup"></a>
## 1. 初回セットアップ

### 1-1. 必要なものを確認する

| 項目 | 必要なもの |
|---|---|
| Mac | Apple Silicon搭載機。Intel Macは対象外 |
| macOS | 26以降 |
| Apple container | このプロジェクトの動作確認に使用した版は1.2.2。未導入なら以下の手順で導入 |
| Python | Mac側にPython 3.9以降 |
| 開発ツール | Apple Command Line Tools。Saveの補助プログラムを初回にコンパイルするために使用 |
| メモリ | 16GB以上を推奨 |
| ストレージ | ROSや開発ツールを含む環境・ビルドキャッシュ用に数十GB以上の空き。イメージ保存にはさらに空きが必要 |
| インターネット | 初回のイメージ・パッケージ取得に使用 |
| 接続ソフト | ブラウザ。RDPを使う場合はRDPクライアントも用意 |

Macの「ターミナル」を開き、次を確認してください。

```bash
uname -m
sw_vers -productVersion
python3 --version
```

`uname -m`が`arm64`なら対象のMacです。Pythonがない場合は、[Python公式サイト](https://www.python.org/downloads/macos/)から導入してから進めてください。

Command Line Toolsが未導入なら、Macで`xcode-select --install`を実行してインストールを完了してください。

このガイドでは、コマンドの実行場所を「Macのターミナル」「Ubuntu内の端末」と明記します。
場所を取り違えると動きません。コード欄のコマンドだけをコピーし、説明文や実行結果は貼り付けないでください。

### 1-2. プロジェクトを取得する

**実行場所：Macのターミナル**

```bash
mkdir -p ~/repos
cd ~/repos
git clone --branch apple-container https://github.com/tatsuyai713/Development-Container-for-ROS2-on-Arm64-Mac.git
cd Development-Container-for-ROS2-on-Arm64-Mac
```

取得済みの方は再度cloneせず、そのフォルダーに移動してください。
以後の`./build.sh`などは、このプロジェクトのフォルダーで実行します。
現行版は`apple-container`ブランチです。旧Docker版の`22.04`・`24.04`ブランチとは手順が異なります。

### 1-3. Apple containerをインストールする

**実行場所：Macのターミナル**

未導入の場合だけ実行します。

```bash
./install-container.sh
```

Apple公式のインストーラーを取得し、署名と公証情報を確認してインストールします。
Macの管理者認証を求められたら、画面の案内に従ってください。
導入済みの場合は、次でバージョンを確認できます。

```bash
container --version
```

### 1-4. Apple containerのサービスを開始する

**実行場所：Macのターミナル**

```bash
./setup.sh
```

`Setup complete`と表示されれば、ビルドに進めます。
「サービス」とはコンテナを動かすMac側の土台です。この時点ではUbuntuのデスクトップはまだ起動していません。

### 1-5. Ubuntuのイメージを作る

「イメージ」は、Ubuntuやアプリをまとめた起動元です。作成には時間がかかるため、完了するまで待ちます。

**実行場所：Macのターミナル**

```bash
./build.sh
```

質問が順番に表示されます。`[...]`内が既定値で、そのままEnterを押すと採用されます。
初めての方は、次を目安に回答してください。

| 質問 | 回答の目安 |
|---|---|
| Ubuntu version | `24.04`が既定。`22.04`・`26.04`も選択可能 |
| Image name / Base image | 通常はEnter。選んだUbuntu版に対応する名前を自動設定 |
| Desktop display language | 日本語なら`jp`、英語なら`en` |
| Physical keyboard layout | 日本語JISキーボードなら`jp`、US配列なら`us` |
| Install ROS 2 development environment | ROS 2を使うなら`true` |
| Install development tools | 一般的な開発やLibreOfficeを使うなら`true` |
| Build virtual CPUs / Build memory | 初回は既定の`4`・`8G`を目安にする |

表示言語とキーボード配列は別の設定です。日本語表示でもUSキーボードを選べます。
日本語入力に必要なMozc等は、表示言語で`jp`を選んだときに追加します。

| Ubuntu | ROS 2 | デスクトップ環境のパッケージ |
|---|---|---|
| 22.04 | Humble | Desktop |
| 24.04（既定） | Jazzy | Desktop Full |
| 26.04 | Lyrical | Desktop Full |

続いて、Ubuntu・ブラウザ・RDPへのログインに使うパスワードを入力します。
これは自分で決める開発環境用のパスワードです。入力中に文字が表示されなくても正常です。
パスワードは設定ファイルには保存しません。

最後に`Built:`とイメージ名が表示されれば完了です。
設定は既定で`configs/default.env`に保存されます。

**26.04を専用の設定で使う場合**は、上の`./build.sh`の代わりに次を実行し、Ubuntu versionの質問に`26.04`と回答します。
ファイル名だけではUbuntu版は変わりません。続く起動でも同じ設定ファイルを指定してください。

```bash
./build.sh --config configs/26.04.env
```

すでにイメージと設定を作成済みなら、ビルドを繰り返さず、次の起動手順へ進めます。

### 1-6. Ubuntuを起動する

**実行場所：Macのターミナル**

```bash
./start.sh
```

26.04用の設定に保存した場合は、上の代わりに次を使います。

```bash
./start.sh --config configs/26.04.env
```

初回は、画面サイズ・接続ポート・CPU・メモリ・共有フォルダーなどを質問します。

| 設定 | 初回の目安 |
|---|---|
| Container name / Persistent /config volume | 通常はEnter |
| Desktop resolution | `1920x1080` |
| DPI / Stream scale / Frame rate | `96` / `1.0` / `30` |
| Timezone | Macから検出した値。日本なら通常`Asia/Tokyo` |
| HTTP / HTTPS host port | 通常はEnter。他の環境と同時起動する場合は別番号にする |
| Enable XRDP | RDPも使うなら`true` |
| Virtual CPUs / Memory / Shared memory | 既定は`4` / `8G` / `4G` |
| Mount macOS home | MacのファイルをUbuntuから使うなら`true` |
| Mount ~/.ssh | MacのSSH設定・鍵を共有する必要がある場合に`true`。不要なら`false` |
| SSL directory | 自分の証明書を使わない場合は空欄 |

共有を有効にしたフォルダーでは、Ubuntuからの編集がMac側のファイルに直接反映されます。
起動時にはクライアント修正と管理アイコンも自動で配置されます。

新しくコンテナを作成すると、最後に`HTTP`・`HTTPS`と、XRDPを有効にした場合の`RDP`接続先が表示されます。
自動でブラウザは開かないため、次の手順で接続します。
既存コンテナの再開では接続先を表示しないため、以前のURLか、次節の確認方法を使ってください。

<a id="connect"></a>
## 2. デスクトップに接続する

### 2-1. 接続先とログイン情報を確認する

| 項目 | 確認する値 |
|---|---|
| ブラウザのURL | `https://127.0.0.1:<HTTPS_PORT>` |
| RDPの接続先 | `127.0.0.1:<RDP_PORT>`。`ENABLE_XRDP=true`の場合のみ利用可能 |
| ユーザー名 | イメージをビルドしたMacユーザーの短い名前 |
| パスワード | `build.sh`で自分が入力したパスワード。Macのログインパスワードと自動同期はしない |

`<HTTPS_PORT>`等は実際の番号に置き換えます。初回作成時の表示を控えていなければ、**Macのターミナル**で設定を確認できます。
26.04用の設定の例です。既定の設定を使った方はファイル名を`configs/default.env`に置き換えてください。

```bash
sed -n -E '/^(UBUNTU_VERSION|CONTAINER_NAME|HTTP_PORT|HTTPS_PORT|ENABLE_XRDP|RDP_PORT)=/p' configs/26.04.env
id -un
```

例えば`HTTPS_PORT=60501`ならブラウザで`https://127.0.0.1:60501`を開きます。
MacのUIDが501でポートを変更していない場合の値です。全員が60501になるわけではありません。
`127.0.0.1`はこのMac自身です。この手順は同じMacから接続するためのものです。

設定ファイルを後から編集しただけでは、既存コンテナのポートは変わりません。
実際の割り当てを確認する場合は`./status.sh --config configs/26.04.env`の出力の`publishedPorts`を見ます。
ブラウザはコンテナ側3001番、RDPは3389番に対応するMac側の`hostPort`を使います。

<a id="browser"></a>
### 2-2. Chrome・Safariのブラウザで接続する

1. コンテナを起動したMacで、**Google ChromeまたはSafari**を開きます。
2. アドレス欄へHTTPSのURLを入力します。例：`https://127.0.0.1:60501`。
3. 自己署名証明書の警告が出る場合は、自分のローカル環境の接続先であることを確認して証明書の信頼設定を行います。独自証明書の設定は[後半の説明](#certificates)を参照してください。
4. ログイン画面で、上で確認したユーザー名とビルド時のパスワードを入力します。
5. UbuntuのKDEデスクトップが表示されるまで待ちます。入力欄をクリックして文字を入力し、操作を確認します。
6. アプリケーションメニューから**Konsole**や**Chrome**を開きます。ここで開くChromeはUbuntu内のアプリです。

これはSelkiesによるブラウザ接続です。RDP接続の設定やアプリは必要ありません。
HTTPのポートも公開しますが、このガイドではクリップボードや映像APIに必要なセキュアな接続を使うため、**HTTPSで接続します**。
Safariのクリップボード操作には、証明書の信頼設定に加えてブラウザのアクセス許可が必要になる場合があります。
音が出ないときは、ページ内をクリックしてから再生し、Macの音量とブラウザのタブの消音設定も確認してください。

<a id="rdp"></a>
### 2-3. RDPクライアントで接続する

1. 起動設定で**Enable XRDP=`true`**にします。すでに無効の設定で作成済みなら、必要なデータを保存してから`./start.sh --reconfigure --config configs/26.04.env`で有効にして再作成します。設定ファイルは自分の環境に合わせてください。
2. MacでRDPクライアントを開き、新しいPCへの接続を追加します。
3. PC名／接続先に`127.0.0.1:3389`など、自分のRDP接続先を入力します。`https://`は付けません。ブラウザ用の60501等は使いません。
4. ユーザー名とパスワードに、2-1で確認した値を入力します。
5. Macで音を聞く場合は、クライアントの音声設定を「このコンピューターで再生」に相当する設定にします。クリップボードも使う場合は、その転送設定を有効にします。
6. 接続を開始します。XRDPのログイン画面でセッションの選択が表示されたら**Xorg**を選び、同じユーザー名とパスワードでログインします。
7. Ubuntuのデスクトップが表示されたら、アプリを開いて操作します。

ブラウザとRDPは別々のデスクトップセッションです。片方で開いたウィンドウは、もう片方には表示されません。
同じUbuntuユーザーのファイルは共有します。Safari用のコピー＆ペーストボタンはRDPには表示されません。
RDPのコピー＆ペーストは、RDPクライアントのクリップボード転送を使います。

<a id="clipboard"></a>
### Safariでコピー＆ペーストする

画面右下に、転送方向を表示した2つのボタンがあります。対象はテキストです。

| やりたいこと | 操作 |
|---|---|
| Macの文字をUbuntuへ貼り付ける | Mac側でコピー → Ubuntu側の貼り付け先を選択 → **Paste: Mac → Container** |
| Ubuntuの文字をMacへコピーする | Ubuntuのアプリでコピー → **Copy: Container → Mac** → Macのアプリで貼り付け |

ボタンを押す前に、コピー元のアプリで通常のコピー操作を行ってください。
エラーはボタンの横に表示されます。文字入力用のダイアログは出しません。
リモート画面上のCmd+Vにも対応しています。権限エラーがある場合はHTTPS・証明書・Safariの許可を確認してください。

<a id="desktop"></a>
## 3. デスクトップのアイコンを使う

ブラウザまたはRDPで開いた**Ubuntuのデスクトップ上**にあるアイコンです。Macのデスクトップのアイコンではありません。
管理アイコンは英語表記です。ダブルクリックして使います。実行許可を確認する画面が出た場合は、ランチャーの実行を許可してください。

| アイコン | 何をするか | 使う場面 |
|---|---|---|
| **Home / ホーム** | Ubuntuユーザーのホームフォルダーを開く | ファイルを探す、`host_home`を開く |
| **Trash / ごみ箱** | ごみ箱を開く | 削除したファイルを確認する |
| **Container Status** | コンテナの動作状態と最新の保存イメージを表示 | 起動状態や次回使用するイメージを確認する |
| **Stop Container** | このUbuntuコンテナを停止する。削除はしない | 今日の作業を終える |
| **Restart Container** | このコンテナを停止して再起動する | 環境を起動し直す |
| **Save Container Image** | 現在の環境を、新しい起動用イメージとして保存する | 追加したアプリや設定を再作成後も使う |

### Home・Trashでファイルを扱う

**Home / ホーム**を開くとUbuntuのホームフォルダーが表示されます。Macのファイルを開くには、その中の`host_home`へ進みます（ホーム共有を有効にした場合）。
**Trash / ごみ箱**はUbuntu側のごみ箱です。共有したMacファイルを削除する前には、実体がMac側にあることを確認してください。

### Container Statusで状態を確認する

1. **Container Status**をダブルクリックします。
2. 表示されたコンテナの状態と、保存済みの場合は次回再作成に使うイメージ名を確認します。
3. OKで閉じます。状態を見るだけなので、コンテナの停止や保存は行いません。

### Stop Container・Restart Containerで終了・再起動する

**Stop Container / Restart Container**では、確認して実行するとブラウザやRDPの接続が切れます。
停止後はMac側で`./start.sh`を実行して再開します。再起動の場合は、起動を待って再接続します。
未保存の編集は先にアプリ内で保存してください。

終了するとき：

1. 作業中の文書やソースコードを保存します。
2. **Stop Container**をダブルクリックし、確認画面でYesを選びます。
3. 接続が切れたら終了です。次回はMacで`./setup.sh`、`./start.sh`を実行し、同じ接続先を開きます。

再起動するとき：

1. 作業を保存し、**Restart Container**をダブルクリックします。
2. 確認画面でYesを選びます。一度接続が切れます。
3. 起動を待ち、ブラウザはページを再読み込み、RDPは同じ接続先へ再接続します。すぐつながらない場合は少し待って再試行します。

### Save Container Imageで環境を保存する

1. アプリ内で編集中のファイルを保存します。
2. アイコンをダブルクリックします。
3. 確認内容を読み、Yes（はい）を選びます。実行しない場合はNo（いいえ）を選びます。
4. 参照元と同じKDEの進捗ダイアログが表示されます。数分以上かかることがあります。完了メッセージが出るまで待ち、連続で実行しないでください。
5. 成功すると、新しいイメージ名とMac側のアーカイブ保存先が表示されます。失敗時は詳細エラーダイアログに理由を表示します。

保存中も**Container Status**で状態を確認できます。保存中のStop・Restart・追加のSaveは、処理中のエラーを表示して実行を見送ります。後から自動で実行する予約にはなりません。

保存対象はディスク上のファイル・アプリ・設定です。開いているウィンドウや実行中のプロセスをそのまま復元する機能ではありません。
保存しても現在のデスクトップはそのまま使えます。元のイメージも残します。
次回`./start.sh --recreate`を実行すると、直近の保存成功時点のイメージを使います。
元のレイヤーを再利用し、追加・変更・削除したファイルだけを新しいレイヤーに保存します。初回は比較用の索引を作るため読み取りに時間がかかります。
同じコンテナでの次のSaveは、前回の保存イメージを親にして変更分だけを追加します。変更したファイルはファイル単位で保存し、ファイル内部の変更バイトだけを保存する方式ではありません。
新しいイメージ名と差分アーカイブは保存ごとに増えますが、変更していない元のレイヤーを毎回複製することはありません。

この操作は、アプリで文書を保存する操作とは別です。また、Macの共有フォルダーや`/config`の内容はイメージには入りません。
それらのデータは、それぞれの保存先で管理します。詳しくは次の「ファイルを保存する」を参照してください。

<a id="daily"></a>
## 4. 毎日の起動と終了

### 次の日も使う

**実行場所：Macのターミナル。プロジェクトのフォルダー内**

```bash
./setup.sh
./start.sh
```

その後、ブラウザやRDPで接続します。普段の起動で`./build.sh`をやり直す必要はありません。
複数の設定がある場合は、`start.sh`が表示するメニューで使いたい環境を選びます。
毎回同じ26.04環境を開く場合は、`./start.sh --config configs/26.04.env`と明示できます。
接続したら、[ROS 2の使い方](#usage)や[Desktopアイコン](#desktop)の手順へ進んでください。

### 今日の作業を終える

Ubuntuのアプリでファイルを保存してから、**Stop Container**を使います。
Macから停止する場合は、次でも停止できます。

```bash
./stop.sh
```

停止だけなら、コンテナ内で追加したファイル・アプリ・設定は残ります。
毎回イメージ保存をする必要はありません。ブラウザのタブを閉じるだけではコンテナは停止しません。

### 状態を見る・再起動する

**Macのターミナル**で実行します。

```bash
./status.sh
```

```bash
./restart.sh
```

これらの操作は最後に起動した設定を使います。記録がなければ存在する環境から選び、対象が複数で決められない場合は選択を求めます。
`--config configs/26.04.env`のように、対象の設定を明示することもできます。

<a id="files"></a>
## 5. ファイルを保存する・Macと共有する

**停止**は環境を残したまま休止すること、**再作成**は起動元のイメージからコンテナを作り直すことです。
再作成では、最後のイメージ保存以降にコンテナ内だけで変更した内容は引き継がれません。

| 保存場所・内容 | 停止→起動 | コンテナの再作成 | Save Container Imageに含むか |
|---|---|---|---|
| `~/host_home`以下のMacファイル | 残る | 同じMacフォルダーを共有すれば残る | 含まない。実体はMac側 |
| `/config`以下のデータ | 残る | 同じ永続ボリュームを使えば残る | 含まない。実体は別ボリューム |
| 通常のUbuntuホーム、Desktop、Documents等 | 残る | 選んだイメージに保存されている時点まで戻る | 含む。ただし共有マウント部分を除く |
| Ubuntu内で追加したアプリ・システム設定 | 残る | 選んだイメージの状態になる | 含む |

`/config`を永続化しているからといって、すべてのホームフォルダーやアプリ設定が自動でそこへ保存されるわけではありません。
重要なソースコードや文書は、保存場所を自分で確認してください。

### Macとの共有フォルダーを使う

起動時に`Mount macOS home=true`を選んだ場合、UbuntuのHomeを開き、`host_home`へ進むとMacのホームフォルダーが見えます。
例えば、Ubuntuの`~/host_home/ros2_ws`はMacの`~/ros2_ws`と同じ場所です。

Ubuntu内の端末から作業用フォルダーを作る例です。

```bash
mkdir -p ~/host_home/ros2_ws/src
```

この場所なら、コンテナを作り直してもソースコードをMac側に残せます。
共有フォルダー内の編集・削除はMac側へ直接反映され、コピーを別に作る仕組みではありません。
`MOUNT_HOME=false`の場合はこの共有がないため、必要なファイルを別の方法でMacへ退避してください。

<a id="usage"></a>
## 6. ROS 2やアプリを使う

### Ubuntu内の端末を開く

デスクトップのアプリケーションメニューで`Konsole`を検索して開きます。
以後この節のコマンドは、**Ubuntu内の端末**で実行します。

### ROS 2の動作を確認する

ビルド時にROS 2を有効にした環境で実行してください。まず、その端末でROS環境を読み込みます。

```bash
source "/opt/ros/$(cat /etc/ros-distro)/setup.bash"
ros2 --help
```

ROS環境は端末ごとに読み込む必要があります。別のKonsoleを開いた場合も`source`を実行してください。

メッセージ送受信を試すには、端末を2つ使います。

**Ubuntu内の端末1：送信側**

```bash
source "/opt/ros/$(cat /etc/ros-distro)/setup.bash"
ros2 run demo_nodes_cpp talker
```

**Ubuntu内の端末2：受信側**

```bash
source "/opt/ros/$(cat /etc/ros-distro)/setup.bash"
ros2 run demo_nodes_cpp listener
```

送信・受信のログが増えれば動作しています。それぞれCtrl+Cで終了します。
これはコンテナ内での確認です。実機ロボットや別PCとのROS通信は、別途ネットワーク設定が必要です。

### 自分のROS 2パッケージを作る

Macホームの共有を有効にした環境での例です。

```bash
source "/opt/ros/$(cat /etc/ros-distro)/setup.bash"
mkdir -p ~/host_home/ros2_ws/src
cd ~/host_home/ros2_ws/src
ros2 pkg create --build-type ament_cmake my_first_package
cd ..
colcon build --symlink-install
source install/setup.bash
```

これで、Macにソースコードを残しながらUbuntuでビルドできます。
生成されるプログラムはLinux arm64用です。Macのアプリとして直接起動するものではありません。

### ブラウザ・文書・開発ツールを使う

- アプリケーションメニューで`Chrome`を検索すると、Ubuntu内のGoogle Chromeを使えます。
- 開発ツールを有効にしたイメージには、Git、C/C++・Python開発ツール、Vim、Emacs、tmux、LibreOffice等を導入します。
- 日本語を選んだイメージでは、入力メソッドのメニューからMozcを選んで日本語入力を使えます。
- ブラウザ接続の音声とRDPの音声は接続経路が異なります。RDPではMac側クライアントの音声転送設定も確認してください。

<a id="save"></a>
## 7. 環境を保存・復元・更新する

この節の操作は**Macのターミナル**から行います。複数環境がある場合は、ビルドと起動の両方で同じ設定を指定してください。
例えば26.04では`./build.sh --config configs/26.04.env`、`./start.sh --recreate --built-image --config configs/26.04.env`のように指定します。
`--recreate`は現在のコンテナを削除して作り直すため、変更前に保存場所を[ファイルの保存の説明](#files)で確認してください。

### 作業環境の変更を保存して、作り直す

1. 重要な文書やコードをアプリ内で保存します。
2. **Save Container Image**を実行し、成功メッセージを確認します。
3. 必要なら**Container Status**で、次回使用する保存イメージを確認します。
4. **Macのターミナル**で次を実行します。

```bash
./start.sh --recreate
```

現在のコンテナが置き換わり、最新の保存成功時点から起動します。ブラウザやRDPは再接続してください。
最後のイメージ保存後にコンテナ内だけで行った変更は、アプリでファイル保存済みでも引き継がれません。共有フォルダーと永続ボリュームは、同じものを引き続き使います。

既定では、Macの`~/.local/state/ros2-container-control/`以下に保存情報とOCIアーカイブを置きます。
保存イメージは一意の`saved-...`タグで管理し、保存が失敗した場合は次回使用するイメージを変更しません。
この保存は、データベース等へ整合性確保を指示する専用バックアップの代わりにはなりません。

### ビルドした状態へ戻す

保存イメージではなく、ビルド設定に書かれたイメージから作り直す場合です。
現在のコンテナ内だけにある変更は、先に保存・退避してください。

```bash
./start.sh --recreate --built-image
```

### 言語・Ubuntu版・導入ツールを変更する

これらはイメージを作るときの設定です。ビルドし直した後、**新しくビルドしたイメージを指定して**再作成します。

```bash
./build.sh
./start.sh --recreate --built-image
```

対話ビルドは毎回プロジェクト既定値から質問します。前回と同じビルド設定を使う場合は次にします。
パスワードが環境変数で指定されていなければ、再度入力を求めます。

```bash
./build.sh --non-interactive
./start.sh --recreate --built-image
```

### 解像度・CPU・メモリ・接続ポートを変える

```bash
./start.sh --reconfigure
```

実行設定を質問し直してコンテナを再作成します。ビルドし直す必要はありません。
保存イメージがあればその最新のものを使うため、実行前に必要な変更を保存してください。

### コンテナを削除する

普段の終了には**Stop Container**を使ってください。削除は、環境を片付けたい場合の操作です。

```bash
./delete.sh
```

表示された対象を確認し、削除する場合だけ`y`を入力します。既定ではイメージと`/config`ボリュームを残します。
`./delete.sh --volume`は`/config`の永続データも削除します。Macの共有フォルダー自体を削除する操作ではありません。

<a id="troubleshooting"></a>
## 8. 困ったとき

| 症状 | 最初に確認すること |
|---|---|
| Apple containerのサービスが停止している | Macで`./setup.sh`を実行してから`./start.sh` |
| `Container ... not found`と出る | 対象コンテナがあるか`container list --all`で確認。削除済みなら対象の設定を指定して`start.sh`から作成 |
| 接続先が開かない | `container list`で起動を確認。起動時に表示されたURL・ポートを使う |
| ログインできない | `id -un`で短いユーザー名を確認。ビルド時のパスワードを使用 |
| ポートが使用中と言われる | 同じ番号の別コンテナを停止するか、起動設定のポートを変更 |
| Safariで文字を入力できない | Ubuntuの入力欄をクリック。古い画面ならページを再読み込みし、下記のクライアント更新を実行 |
| Safariのコピー操作が拒否される | HTTPS・証明書の信頼・Safariのクリップボード許可と、ボタン横のエラーを確認 |
| Windows Appで双方向設定なのにコピペできない | 接続先のDevices & AudioでClipboardをBidirectionalに設定。改善しなければ、下記のWindows App完全終了を試す |
| RDPの時計が9時間ずれる | 古い環境はシステム側がUTCのままの場合がある。`./update-client.sh <コンテナ名>`で起動設定のタイムゾーンをシステムにも反映 |
| RDPで音が出ない | RDPクライアントでMac側への音声再生を有効にする |
| 管理アイコンがない・Macが応答しない | 下記の管理機能の再導入を実行。コンテナは起動した状態にする |
| Saveで`could not read block`と出る | 古い全体保存の実装。`desktop-actions.sh`で管理機能を更新する。現在の差分保存は標準exportを使わない |
| SaveでCommand Line Toolsのエラー | Macで`xcode-select --install`を完了してから再試行 |
| Saveで別の操作が実行中と出る | 現在の保存等が終わるまで待つ。連続実行しない |
| 空き容量が減った | Saveごとのイメージ・アーカイブ、ビルドキャッシュが増えていないか確認 |

### Windows Appのクリップボードが動かない

Clipboardが**Bidirectional（双方向）**でも、Windows App側の転送処理が応答しなくなる場合があります。
この環境では、XRDPの転送チャネルの交渉が成功していてもテキスト要求への応答が届かず、Windows Appの完全終了・再起動で復旧した事例を確認しています。
接続だけの切断・再接続では改善しない場合があります。

1. 接続中の環境で作業を保存します。次の操作ではWindows App内のほかのRDP接続も切れます。
2. Macのメニューバーで**Windows App → Quit Windows App**（⌘Q）を選び、アプリ自体を完全に終了します。接続画面を閉じるだけでは不十分です。
3. Windows Appを起動し直し、対象のUbuntuへ再接続します。
4. Macで短いテキストを新しくコピーし、Ubuntuのアプリで右クリックの「貼り付け」を試します。
5. UbuntuからMacへのコピーも確認します。Konsoleのキー操作はCtrl+Shift+C／Ctrl+Shift+Vです。

この症状への対処として、最初からコンテナの再作成や保存イメージの復元を行う必要はありません。
完全終了でも直らない場合は、XRDPの設定・転送プロセス・ログを調べて切り分けます。

### 起動中のコンテナ名を調べる

**Macのターミナル**で実行します。

```bash
container list
```

以後の`<コンテナ名>`は、この一覧の対象の名前に置き換えてください。山括弧は入力しません。

クライアント修正を反映する場合：

```bash
./update-client.sh <コンテナ名>
```

管理アイコンとMac側サービスを導入・更新する場合：

```bash
./desktop-actions.sh <コンテナ名>
```

後者は、既存コンテナではMacホームの共有、再作成したコンテナでは専用の管理用共有を使います。
どちらもない古い環境では、必要なデータを保存してから`start.sh`による再作成が必要です。

### ログ・容量を確認する

選択したコンテナのログを表示します。表示終了はCtrl+Cで、コンテナ自体は停止しません。

```bash
./logs.sh
```

Mac側の管理機能のエラーを確認します。

```bash
tail -n 60 ~/.local/state/ros2-container-control/agent.log
```

Macの空き容量と、コンテナ関連の使用量を確認します。

```bash
df -h .
container system df
```

`./prune.sh`は確認後にdangling image（タグのない不要なイメージ）を削除します。
`saved-...`タグの付いた保存イメージや保存アーカイブを一括で削除する機能ではありません。
黒画面やRDPが直ちに終了する場合は、ログと使用イメージを確認してください。
`update-client.sh`はブラウザ側の修正を反映しますが、XRDPやUbuntu側のパッケージは更新しません。
それらの修正には、必要なファイルをMac等へ退避し、現在のプロジェクトのソースでビルドしてから`--recreate --built-image`で再作成します。
保存イメージは元に戻すために残せますが、古い保存イメージで再作成するだけでは新しいビルドの修正は入りません。

<a id="commands"></a>
## 9. コマンド一覧と複数環境

以下は**Macのターミナル**で、プロジェクトのフォルダーから実行します。

| コマンド | 用途 |
|---|---|
| `./install-container.sh` | Apple containerを導入 |
| `./setup.sh` | Mac側サービスを開始・確認 |
| `./build.sh` | イメージの設定を選んでビルド |
| `./build.sh --non-interactive` | 保存済みビルド設定でビルド |
| `./start.sh` | コンテナを起動。複数設定があれば選択 |
| `./start.sh --recreate` | 最新の保存イメージ、なければ設定上のイメージから再作成 |
| `./start.sh --recreate --built-image` | 設定上のビルドイメージから再作成 |
| `./start.sh --reconfigure` | 実行設定を編集して再作成 |
| `./start.sh --non-interactive` | 対話なしで起動。設定未完了・選択不明なら失敗 |
| `./stop.sh` / `./restart.sh` | 選択したコンテナを停止／再起動 |
| `./shell.sh` | Macの端末からコンテナ内のBashを開く。終了は`exit` |
| `./status.sh` / `./logs.sh` | 選択したコンテナの状態／ログを表示 |
| `./update-client.sh <コンテナ名>` | 実行中の画面・入力・クリップボード修正を更新 |
| `./desktop-actions.sh <コンテナ名>` | 実行中の環境に管理アイコンを導入・更新 |
| `./delete.sh` | 確認後に削除。イメージと永続ボリュームは保持 |
| `./delete.sh --volume` | 永続ボリュームも削除 |
| `./prune.sh` | 確認後にdangling imageを削除 |

### Ubuntu版ごとに設定を分ける

例えば26.04専用の設定ファイルを作る場合です。
ビルドの質問で必ず`26.04`を選んでください。**設定ファイル名だけではUbuntu版は切り替わりません。**

```bash
./build.sh --config configs/26.04.env
./start.sh --config configs/26.04.env
```

22.04や24.04も別の設定ファイルに保存できます。同時に使う場合は、HTTP・HTTPS・RDP等のポートを重複させないでください。
生成するコンテナ・イメージ・ボリュームの名前にはユーザー名とUbuntu版を含めます。
既存環境を残して別のUbuntu版を試す場合は、設定を分けてください。

Build・Start・Deleteに加え、Stop・Restart・Shell・Status・Logsも`--config`に対応しています。
起動時に選んだ設定を記録するため、26.04を起動した後の`./stop.sh`等もその環境を対象にします。
記録がない場合は存在するコンテナの設定から選びます。候補が複数で決まらない非対話実行では、
勝手に24.04等を選ばず、`--config`の指定を求めて終了します。

```bash
./stop.sh --config configs/26.04.env
./restart.sh --config configs/26.04.env
./shell.sh --config configs/26.04.env
./status.sh --config configs/26.04.env
./logs.sh --config configs/26.04.env
./delete.sh --config configs/26.04.env
```

`CONFIG_FILE=configs/26.04.env ./stop.sh`という指定も引き続き使えます。
各実行操作の`--non-interactive`は選択質問を禁止します。`start.sh`自体は、明示指定がなく設定が複数ある場合にメニューを表示します。

### Apple containerサービス全体を操作する

```bash
./container-service.sh status
./container-service.sh start
```

`./container-service.sh stop`と`./container-service.sh restart`は、このプロジェクト以外も含めた全コンテナに影響します。
日常の終了には、特定の環境だけを停止する**Stop Container**か`./stop.sh`を使ってください。

<a id="technical"></a>
## 10. 技術的な仕組みと制約

ここからは構成の変更や仕組みを確認したい方向けです。通常の利用だけなら、前半の手順で操作できます。

### 実行基盤とビルド

Apple `container`は、コンテナごとに軽量Linux VMを使います。Macのカーネルを直接共有するLinuxではありません。
ビルド・実行とも`linux/arm64`を指定し、ビルド処理でもUbuntu版とDebianアーキテクチャを検証します。

| Ubuntu | 既定ベースイメージ | ROSパッケージ |
|---|---|---|
| 22.04 | `ghcr.io/tatsuyai713/webtop-kde-base-arm64-u22.04:1.1.0` | `ros-humble-desktop` |
| 24.04 | `ghcr.io/tatsuyai713/webtop-kde-base-arm64-u24.04:1.1.0` | `ros-jazzy-desktop-full` |
| 26.04 | `ghcr.io/tatsuyai713/webtop-kde-base-arm64-u26.04:1.1.0` | `ros-lyrical-desktop-full` |

Jammy arm64では対応するDesktopパッケージを使います。ベースイメージのUbuntu版は選択した版と一致する必要があります。
`Containerfile`と`rootfs/install-development.sh`でXRDP、ROS、colcon、rosdep、任意の開発ツールを導入します。
`rootfs/customize-user.sh`がMacとLinuxのユーザー名・UID・GIDを合わせ、認証情報とデスクトップの初期設定を準備します。
パスワードは通常のbuild argではなくBuildKit secretで渡します。設定ファイルへ保存しません。

Linux arm64版Google Chrome Stableは、開発ツールを無効にしても導入します。
Google公式の`google-chrome-stable_current_arm64.deb`を取得し、パッケージ名とarm64であることを検証します。

22.04はchecksumを固定したJammy互換のPixelFlux wheelへ差し替えます。
新しいwheelに含まれるFFmpegが要求する`vaMapBuffer2`をJammyのlibvaが提供しないためです。
24.04はベース付属のPixelFluxを使用します。

### 設定の反映時点

| 設定 | 反映する操作 |
|---|---|
| Ubuntu・ROS・言語・キーボード・導入ツール | ビルドしてから`start.sh --recreate --built-image` |
| ポート・解像度・DPI・CPU・メモリ・マウント | `start.sh --reconfigure`、または設定を編集して`--recreate` |
| クライアント修正 | `start.sh`で自動適用。実行中は`update-client.sh`でも適用可能 |
| デスクトップの管理機能 | `start.sh`で配置。実行中は`desktop-actions.sh`でも配置可能 |

`build.sh`は通常`configure.sh --build`を呼び、ビルドの質問をプロジェクト既定値へ戻します。
`--non-interactive`では保存設定を再利用します。
実行設定は、初回または`--reconfigure`時だけウィザードで質問します。
タイムゾーンはMacから検出し、取得できない場合は`UTC`です。
起動時に`TZ`だけでなく`/etc/localtime`と`/etc/timezone`にも反映するため、環境変数を引き継がないRDPセッションでもブラウザと同じ時刻を表示します。

独自のベースイメージやキャッシュなしビルドを使う場合：

```bash
BASE_IMAGE=ghcr.io/example/image:tag ./build.sh
```

```bash
NO_CACHE=true ./build.sh
```

### 画面・入力・音声

s6がX11、KDE Plasma、音声、認証、nginx、Selkiesを起動します。
ブラウザはXディスプレイ`:1`を配信し、XRDPは別のXorgXRDPセッションを作ります。
ブラウザとRDPでファイルは共有しますが、表示サーバーと実行中のアプリは別です。

26.04では、単一画面をSelkiesの別名仮想モニターに置き換えない補正を行い、Plasma 6の黒画面を防ぎます。
XRDPは専用のセッションスクリプトを使い、systemd journalを要求する`im-launch`を経由しません。
XRDPのPlasma用ランタイムディレクトリを分け、PipeWireの接続先は共通に維持します。

22.04・24.04ではPulseAudioの対応版に対してXRDP音声モジュールをビルドし、26.04ではPipeWire用モジュールを使います。
XRDPアプリの音声接続先をセッションごとに設定し、ブラウザの音声出力を奪わないようにします。
日本語入力は22.04・24.04でFcitx、26.04でFcitx 5とMozcを使用します。

Safariでは編集可能なキーボード補助欄へフォーカスし、通常入力とIMEはSelkies本体で扱います。
処理済みのEnterを補助処理から再送信しません。画面を離れたとき等にはキーを解放します。
クリップボードは画面内のボタンとネイティブpasteイベントを使い、Linux側への書き込み後に貼り付け操作を送ります。
元の画面ファイルの再配置後に修正を再適用し、配信ファイルのキャッシュも更新します。

### 描画・高速化・画質

LinuxのOpenGL描画はMesa llvmpipeによるCPU処理で、送信映像のエンコードもソフトウェアです。
MacのMetal・Apple GPUをLinuxアプリへ渡す機能は、このプロジェクトにはありません。
ARM64のCPU仮想化やNEON等のCPU命令は利用できます。

受信するMac側のChrome・SafariではH.264のハードウェアデコードを優先します。
実際の映像のSPSからプロファイル・制約・レベルを読み取り、非対応の場合は自動選択・ソフトウェアへ切り替えます。
これはMac側の映像再生の処理で、Ubuntu内のGPU利用を意味しません。

`KWIN_EFFECTS_FORCE_ANIMATIONS=1`を既定にして、CPU描画でもKWinのアニメーションを許可します。
個々の効果はKDEのシステム設定で選択できます。高解像度・高フレームレート・重い効果はCPU負荷を増やします。
`DPI`は文字・フォントの倍率、`STREAM_SCALE`は配信映像の寸法、`FRAMERATE`は目標フレームレートです。
Retinaブラウザのdevice pixel ratioでは設定済みDPIを上書きしません。
`RESOLUTION`はブラウザ用Ubuntuデスクトップの解像度です。ブラウザのウィンドウを変更すると、
縦横比を保ったまま表示だけを自動で拡大・縮小します。Ubuntuの解像度と映像処理の画素数は増えません。
設定済みFPSとデスクトップ効果は維持されます。RDPは別のデスクトップで、サイズはRDPクライアント側で指定します。

### ポートと共有

Webの既定ポートは`50000 + MacのUID`、HTTPSは`60000 + UID`です。
RDPは3389、Foxglove用は8765、ROS bridge用は9090を既定とします。
すべてMacのloopback（`127.0.0.1`）へ公開します。
Foxglove・ROS bridgeはポートの用意だけで、対応ノードを自動起動しません。
実機ロボット等との通信では、個別のネットワーク設計が必要です。

`CONFIG_VOLUME`を`/config`へマウントします。`MOUNT_HOME`・`MOUNT_SSH`でMac側の共有を選択できます。
<a id="certificates"></a>

独自のHTTPS証明書を使う場合は、起動設定の`SSL_DIR`へMac上の証明書フォルダーの絶対パスを指定します。
接続に使うホスト名またはIPを証明書の対象に含め、Mac側でも発行元を信頼する必要があります。
`SSL_DIR`を指定する場合は`cert.pem`と`cert.key`を用意し、`/config/ssl`へ読み取り専用でマウントします。
コンテナ作成時の指定なので、変更時は再作成してください。

### 管理アイコン・保存の仕組み

Mac側のLaunchAgent `io.github.tatsuyai713.ros2-container-control`が、共有フォルダー経由の要求を処理します。
受け付けるのは登録済みの対象コンテナに対する状態確認・停止・再起動・保存だけです。
要求から別コンテナや任意のシェルコマンドを指定することはできません。
新規コンテナには専用の管理用マウントを用意するため、Macホームの共有を無効にしても利用できます。
既存環境への追加時は、利用可能なホストホーム共有を使います。

Saveは、親イメージのOCIレイヤーを保ったまま、変更分のレイヤーを1つ追加する方式です。
親イメージの読み取り専用コンテナでファイルの内容・メタデータの索引を一度作り、実行中コンテナとの差分を求めます。
同じコンテナでの次回Saveでは直前の保存イメージと索引を再利用します。変更していないファイルは、inode・ctime・mtime・サイズで確認し、保存済みのハッシュを利用します。
追加・変更ファイルは内容・所有者・権限・更新日時・拡張属性・リンクを記録し、削除はOCI whiteoutで表現します。
共有マウントと`/proc`・`/sys`・`/dev`・`/run`・`/tmp`・`/config`は対象外です。
稼働中のファイルを読むため、データベース等の整合性を保証する瞬間的なスナップショットではありません。

Apple container 1.2.2で確認した`imageLoad`のXPC経路へ差分OCIを渡し、CLIの`image load`が行う全体展開は保存時に繰り返しません。
Mac側の小さな補助プログラムはCommand Line Toolsで初回にコンパイルします。Apple側の経路が利用できない場合はエラーを表示し、全体保存へ黙って切り替えません。
登録後に設定・親レイヤー・差分レイヤーを検証してから、次回使用するイメージを更新します。
復元時には通常どおり必要なファイルシステムの展開が行われます。

差分アーカイブ・実行設定・ファイル索引はMacの`~/.local/state/ros2-container-control/`以下に保存します。
**差分アーカイブだけでは別のMacへ環境全体を移せません。** 復元には参照する親レイヤーも必要です。
環境全体を別の保存先へ退避するときは、Macで`container image save --output /保存先/backup.tar <保存イメージ名>`を実行してください。
従来作成した全体保存イメージもそのまま使えます。
イメージの実行コマンド・環境変数・ユーザー・作業ディレクトリ・メタデータを引き継ぎます。
ただしイメージだけでは公開ポートや共有マウントを再現できないため、通常の復元には保存済み設定と`start.sh`を使ってください。
ソースコードとして再現可能な環境にする場合は、追加パッケージ等を`Containerfile`や`rootfs/`にも記述します。

### 現在の対応範囲

- Apple SiliconとLinux arm64専用です。
- Docker Compose・Dev Containers・Docker互換APIは提供しません。
- ブラウザとRDPは同じ画面を共有しません。
- LinuxのGPU描画・ハードウェアエンコードは提供しません。
- 保存イメージにボリュームや共有フォルダーのデータは含みません。
- 旧Docker版は`22.04`・`24.04`ブランチに残っています。現行版ではそのDOODスクリプトをそのまま実行できません。

## 参考資料

- [Apple container](https://github.com/apple/container)
- [Apple containerのコマンド資料](https://github.com/apple/container/blob/main/docs/command-reference.md)
- [ROS 2公式資料](https://docs.ros.org/)
- [Selkies](https://github.com/selkies-project/selkies)
- [XRDP](https://github.com/neutrinolabs/xrdp)
- [コピー操作と管理アイコンの参考リポジトリ](https://github.com/tatsuyai713/kde-selkies-webtop-devcontainer)
