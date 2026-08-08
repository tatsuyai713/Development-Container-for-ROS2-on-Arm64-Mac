# Development-Container-for-ROS2-on-Arm64-Mac

[English](README.md)

このリポジトリは
[`Development-Container-for-ROS2-on-Arm64-Mac`](https://github.com/tatsuyai713/Development-Container-for-ROS2-on-Arm64-Mac)
の更新版です。旧版のROS 2開発環境とXRDPデスクトップを継承し、現行実装をApple公式の
[`container`](https://github.com/apple/container) ランタイムへ移行しました。KDE Plasmaには
RDPクライアントとSelkies WebRTCによるブラウザのどちらからでも接続できます。

以前のDocker版はリポジトリの`22.04`・`24.04`ブランチに残しています。
現在の実装は`apple-container`ブランチにあります。

## 更新版の主な機能

- Apple Silicon上のApple `container`によるネイティブ`linux/arm64`ビルドと軽量Linux VM
- Ubuntu 22.04 + ROS 2 Humble Desktop Full、またはUbuntu 24.04 + ROS 2 Jazzy Desktop Full
- `colcon`、`rosdep`、C/C++・Python開発環境、エディター、Git、SSHツール、LibreOffice
- Selkiesブラウザ接続とXRDPの両方に対応したKDE Plasma
- 表示言語（`en`/`jp`）とキーボード（`us`/`jp`）の独立選択
- 英語を既定とし、日本語選択時だけ日本語パッケージを追加
- ビルド時と初回起動時の対話設定、および`configs/default.env`への保存
- Tokyo固定ではなく、起動したMacからタイムゾーンを自動検出
- `/config`の永続化と、macOSホーム・SSHディレクトリの任意マウント
- KDEデスクトップのホーム・ごみ箱アイコン
- build、start、stop、restart、shell、logs、status、確認付きdeleteスクリプト
- ブラウザ、XRDP、Foxglove、ROS bridge用ポートのloopback限定公開

Ubuntu 26.04はまだ選択肢に含めません。対応するarm64 KDE/Selkiesベースイメージと、必要な
ROS・XRDPパッケージ一式を検証できた段階で追加します。

## 必要環境

- Apple Silicon Mac（`arm64`）
- macOS 26以降
- Apple `container` 1.x
- ホストメモリ16GB以上を推奨
- XRDP利用時はRDPクライアント

`install-container.sh` はApple公式Releaseのパッケージを取得し、署名・公証情報を検証して
インストールします。この操作には管理者認証が必要です。

## クイックスタート

```bash
cd /path/to/Development-Container-for-ROS2-on-Arm64-Mac

# 初回インストール時のみ
./install-container.sh

# Apple containerサービスを起動・確認
./setup.sh

# イメージ設定を対話選択してビルド
./build.sh

# 保存済み設定で起動（初回のみ設定ウィザードを表示）
./start.sh
```

ビルドではUbuntu、イメージ名、言語、キーボード、ROS、開発ツール、ビルド用リソースを
質問します。その後にデスクトップ用パスワードを入力しますが、パスワードは設定ファイルへ
保存しません。

初回の起動ではポート、表示、タイムゾーン、実行用リソース、マウント、XRDPの有効・無効を質問します。
回答は`configs/default.env`へ保存し、2回目以降は質問せず再利用します。設定ウィザードを再実行するには
`./start.sh --reconfigure`を、自動処理で実行設定が未完了の場合に質問せず失敗させるには
`--non-interactive`を指定します。

## デスクトップへの接続

macOSユーザーのUIDが501の場合、既定の接続先は次のとおりです。

| サービス | 既定の接続先 | 用途 |
|---|---|---|
| Selkies HTTP | <http://127.0.0.1:50501> | ブラウザデスクトップ |
| Selkies HTTPS | <https://127.0.0.1:60501> | 暗号化ブラウザデスクトップ |
| XRDP | `127.0.0.1:3389` | RDPクライアント |
| Foxglove | `127.0.0.1:8765` | Foxgloveサービス用予約ポート |
| ROS bridge | `127.0.0.1:9090` | ROS bridge用予約ポート |

WebとXRDPではmacOSのユーザー名と`./build.sh`で入力したパスワードを使います。同時利用も
できますが、同一画面の複製ではなく独立したPlasmaセッションです。既定ポートは全て
`127.0.0.1`へbindし、LANへ直接公開しません。

## ビルド時の選択

### UbuntuとROS 2

| Ubuntu | ROSディストリビューション | インストールパッケージ |
|---|---|---|
| 22.04 Jammy | ROS 2 Humble | `ros-humble-desktop-full` |
| 24.04 Noble（既定） | ROS 2 Jazzy | `ros-jazzy-desktop-full` |

ROSを省く場合はビルド時に`INSTALL_ROS2=false`を選びます。有効時は`ros-dev-tools`、colcon、
rosdepも導入します。コンテナの書き込みレイヤーにはworkspaceを自動作成しません。必要な場合は、
削除後も残るホスト側storage（例：`~/host_home/ros2_ws`）に作成してください。ROS環境は自動では
読み込みません。必要なshellで
`source /opt/ros/<distro>/setup.bash`を実行してください。ベースイメージのUbuntu版が選択と
一致しない場合、ビルドは停止します。

### 言語とキーボード

表示言語と物理キーボードはどちらも英語側が既定です。言語とキーボードは独立した設定です。

- `USER_LANGUAGE=en`: 英語ロケール。日本語フォントや入力パッケージを追加しません。
- `USER_LANGUAGE=jp`: 日本語ロケール、フォント、Fcitx、Mozcを追加します。
- `KEYBOARD_LAYOUT=us`: USキーボード。既定値です。
- `KEYBOARD_LAYOUT=jp`: 日本語JISキーボード。

これらはイメージ設定です。変更後は再ビルドし、コンテナを再作成してください。

### 開発ツール

`INSTALL_DEV_TOOLS=true`では旧版の主要ツールを導入します。build-essential、CMake、Git、
Vim、Emacs、tmux、Pythonツール、rsync、SSHツール、ネットワーク・圧縮コマンド、
LibreOffice、`clinfo`などが対象です。小さいイメージが必要なら無効化できます。

## コマンド

| コマンド | 動作 |
|---|---|
| `./install-container.sh` | Apple公式containerパッケージをインストール |
| `./setup.sh` | Apple containerサービスを起動・確認 |
| `./configure.sh` | 保存設定を全て対話編集 |
| `./build.sh` | 対話設定後にarm64イメージをビルド |
| `./build.sh --non-interactive` | 保存済みイメージ設定でビルド |
| `./start.sh` | 保存済み設定で起動し、初回のみ設定ウィザードを実行 |
| `./start.sh --reconfigure` | 実行設定を対話編集してコンテナを再作成 |
| `./start.sh --recreate` | コンテナを置き換えて現在の実行設定を再適用 |
| `./start.sh --non-interactive` | 保存済み設定で起動し、実行設定が未完了なら失敗 |
| `./stop.sh` | コンテナを停止 |
| `./restart.sh` | コンテナを再起動 |
| `./shell.sh` | コンテナ内で対話Bashを開く |
| `./logs.sh` | サービスログを追跡 |
| `./status.sh` | 状態とリソース使用量を表示 |
| `./delete.sh` | 確認後にコンテナを削除し、イメージとvolumeは保持 |
| `./delete.sh --volume` | `/config`の永続volumeも削除 |
| `./prune.sh` | dangling imageを削除 |

BuildとStartは`--config path`にも対応するため、設定を分けた複数デスクトップを管理できます。

自動生成するコンテナ名、イメージ名、volume名にはUbuntu版が入ります。例えば
`development-container-for-ros2-on-arm64-mac-$USER-u22.04`と、対応する`-u24.04`名です。
1つの設定ファイルを毎回書き換えず両方を管理するには、Ubuntu版ごとに設定を分けます。

```bash
./build.sh --config configs/22.04.env
./start.sh --config configs/22.04.env

./build.sh --config configs/24.04.env
./start.sh --config configs/24.04.env
```

両方を同時起動する場合は、それぞれの設定で異なるhost portを指定してください。旧版で作成した
設定ファイルの明示的な名前はそのまま維持します。その設定のUbuntu版をビルドウィザードで変更した
場合は旧自動生成名を新しいUbuntu版へ更新しますが、以前のコンテナ、イメージ、volumeは削除しません。

## 設定が反映されるタイミング

設定の適用時点を明確に二段階へ分けています。

| 設定種別 | 例 | 反映時点 |
|---|---|---|
| イメージ | Ubuntu、ROS、言語、キーボード、ツール | `./build.sh`によるイメージ作成時 |
| 実行 | ポート、解像度、タイムゾーン、CPU、メモリ、マウント | `./start.sh`によるコンテナ作成時 |

既存コンテナは作成時の実行設定を保持します。実行設定を対話編集して反映するには
`./start.sh --reconfigure`を使います。設定ファイルを手動編集した後は`./start.sh --recreate`を実行してください。再作成では
named volumeを保持し、コンテナの書き込みレイヤーを破棄します。イメージ設定を変更した場合だけ
再ビルドも必要です。

デスクトップの文字・フォント描画では設定済みの`DPI`を常に使用します。Retinaブラウザからの
device pixel ratioでは上書きされず、`STREAM_SCALE`は配信画面の寸法だけを変更します。

タイムゾーンの既定値は設定初期化時にMacから検出し、取得できない場合だけ`UTC`を使います。

一回だけ別のベースイメージを使う場合:

```bash
BASE_IMAGE=ghcr.io/example/image:tag ./build.sh
```

BuildKitキャッシュを使わずにビルドする場合:

```bash
NO_CACHE=true ./build.sh
```

## ストレージ・セキュリティ・削除

- `/config`は`CONFIG_VOLUME`で指定したnamed volumeを使用します。
- macOSホームは`~/host_home`へ任意でマウントできます。
- ホストの`~/.ssh`はコンテナ内の同じパスへ任意でマウントできます。
- `SSL_DIR`指定時は`/config/ssl`へread-onlyでマウントします。
- ブラウザ、RDP、Foxglove、ROS bridgeポートはloopbackだけに公開します。
- ビルド用パスワードは通常のbuild argではなく、一時的なBuildKit secretで渡します。

`./delete.sh`は対象コンテナ、イメージ、volumeの扱いを表示してから確認します。既定では
イメージとvolumeを残します。`--volume`は永続データも削除し、明示的な自動処理では`--yes`で
確認を省略できます。

## 旧版からの移行

Apple `container`の新規環境では`apple-container`ブランチのスクリプトを使ってください。
旧DockerスクリプトとDockerfileはリポジトリの`22.04`・`24.04`ブランチから参照できます。
ホスト文書は既定の`~/host_home`マウントで移動でき、ROS workspaceは導入済みのcolconと
rosdepで再構築できます。コンテナ削除後も残すworkspaceは`~/host_home`以下に作成してください。

旧版のCommit・Flattenデスクトップ操作は現行版へ移していません。Apple `container`はゲストへ
Docker socketを公開しないためです。恒久的なシステム変更は`Containerfile`または`rootfs/`へ
記述し、`./build.sh`と`./start.sh --recreate`で再現します。ホーム・ごみ箱アイコンは提供します。

## 現在の制約

- Apple Siliconと`linux/arm64`専用です。
- ベースイメージはarm64 manifestを持ち、選択したUbuntu版と一致する必要があります。
- 描画とSelkies encodeはsoftware処理のため、CPU負荷が高くなる場合があります。
- ブラウザとXRDPは独立したPlasmaセッションです。
- Foxglove・ROS bridge用ポートは公開しますが、application nodeは自動起動しません。
- Docker Compose、Dev Containers、Ubuntu 26.04、デスクトップからのホストruntime操作は未対応です。

## 公式資料

- [Apple container](https://github.com/apple/container)
- [Apple container command reference](https://github.com/apple/container/blob/main/docs/command-reference.md)
- [ROS 2 installation documentation](https://docs.ros.org/en/jazzy/Installation.html)
- [Selkies](https://github.com/selkies-project/selkies)
- [XRDP](https://github.com/neutrinolabs/xrdp)

## 更新版コンテナの詳しい仕組み

### 1. ホストruntimeと分離

`setup.sh`がAppleの補助サービスを起動します。Apple `container`はAppleの仮想化基盤を使い、
各Linuxコンテナを軽量VM内で動かします。LinuxはmacOS kernelを共有しません。ビルドと実行は
`linux/arm64`を要求し、イメージ設定処理でもDebian architectureを再確認します。

### 2. 設定の流れ

`build.sh`は`configure.sh --build`を呼びます。`start.sh`が`configure.sh --runtime`を呼ぶのは、
設定ファイルがない初回または`--reconfigure`指定時だけです。どちらもshell-safeな値を同じ
envファイルへ書きます。ビルド設定はイメージ内のファイルと
パッケージになり、実行設定は`container run`引数になります。そのため作成済みコンテナへ
実行設定を後付けできません。`--reconfigure`では新しい実行設定を反映するためコンテナを再作成します。

### 3. イメージ構築

Apple BuildKitが`Containerfile`と選択したKDE/Selkies arm64ベースを読み込みます。最初に
`rootfs/install-development.sh`がUbuntu版を検証し、XRDP、XorgXRDP、対応するROS apt source、
Desktop Full、rosdep、colcon、任意の開発アプリを導入します。Ubuntu 24.04ではPipeWireの
XRDP moduleも導入します。

続いて`rootfs/customize-user.sh`がLinuxのユーザー名・UID・GIDをMac側へ合わせ、一時secretから
Linux・Web認証を設定し、標準ディレクトリを準備します。さらにlocale、XKB、
KDE既定値、ホーム・ごみ箱アイコンを設定します。日本語パッケージは日本語ビルド時だけ導入します。

### 4. VMとサービスの起動

`start.sh`が`/config` volumeを用意し、VMリソース、共有メモリ、loopback port forwarding、
環境変数、任意のbind mountを組み立てます。VM内ではイメージのs6 init treeが仮想display、
KDE Plasma、audio、認証、Selkiesを起動します。追加したs6 serviceはXRDP有効時にD-Bus、
`xrdp-sesman`、`xrdp`を依存順に起動します。

### 5. ブラウザとRDPの表示経路

ブラウザ経路ではPlasmaをX display `:1`へMesa llvmpipeでsoftware描画します。Selkiesがdisplayを
captureしてsoftware encodeし、映像・音声をブラウザへ送り、キーボード・pointer・microphone入力を
戻します。`STREAM_SCALE`はdesktop解像度と独立して配信解像度を下げ、`SELKIES_FRAMERATE`は
目標frame rateを制御します。

RDP経路はコンテナ3389番で待機します。認証後、`xrdp-sesman`が別のXorgXRDP displayを作成し、
独立したD-Bus sessionで`startplasma-x11`を起動します。両経路は同じLinux accountとstorageを
使いますが、display serverとapplication processは共有しません。

### 6. 永続化の境界

イメージには再現可能なOS packageとプロジェクト既定値を入れます。コンテナの書き込みlayerは
使い捨てです。`/config`はnamed volumeで再作成後も残り、bind mountは選択したmacOSファイルを
直接公開します。このためsystem packageはイメージ、desktop application stateは`/config`、
ホスト文書はbind mountで管理します。プロジェクトの永続volumeを意図的に消す操作は
`delete.sh --volume`だけです。
