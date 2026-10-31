# TOTEM Local

Aplicativo local para macOS: editor visual do seu TOTEM e painel nativo SwiftUI sempre acima das outras janelas. Não depende de GitHub Actions.

Abra `../TOTEM Local.app`. O menu ⌨ TOTEM permite reabrir o painel e o editor. O painel não recebe foco de teclado. Fechar uma janela não encerra o aplicativo; use Sair no menu para isso.

## Usar

- Clique em uma das 38 teclas, selecione a função e clique em Aplicar à tecla.
- Use Salvar para gravar no Mac. Cada alteração cria um backup do `.keymap`.
- Carregar no esquerdo/direito compila automaticamente se necessário. Quando solicitado, dê dois toques rápidos no RESET da metade escolhida.
- Uma confirmação de gravação exige um relatório do firmware com a versão esperada, não apenas copiar o UF2.
- A metade esquerda é a central e precisa estar conectada para enviar as teclas ao computador. As duas precisam estar ligadas para o conjunto funcionar.

O painel mostra bateria estimada de cada lado, saída selecionada, camada ativa, posições pressionadas e a saída HID gerada pelo ZMK. O texto final e os acentos dependem do layout e da composição de texto do macOS. O campo nativo no topo do editor permite testar texto recebido pelo macOS sem usar outro aplicativo.

Em USB, os eventos chegam por CDC e são enviados ao painel sem esperar o relatório periódico de bateria. No modo sem fio, o botão Bluetooth do app usa CoreBluetooth e pode solicitar a permissão normal do macOS. O teclado precisa estar pareado no perfil selecionado; permitir a telemetria Bluetooth não substitui o pareamento HID. A telemetria sem fio deve ser validada com o teclado real antes de considerá-la confirmada.

## Arquivos e ambiente

- `../config/totem.keymap`: layout completo original do PR #2, com macros e comportamentos preservados.
- `../config/backups`: backups das alterações locais.
- `../telemetry`: módulo de firmware que expõe somente telemetria local por USB e GATT criptografado.
- `../artifacts`: UF2s, hashes e histórico de mapas por versão.
- `../devices.json`: identificação física de cada metade por serial USB.
- `../native`: código AppKit/SwiftUI/CoreBluetooth do app.
- `http://127.0.0.1:8767`: editor HTML servido somente em loopback.

Python e o ambiente `.venv` ficam nesta pasta. O Docker/Colima mantém a toolchain e as dependências no volume `totem-local-workspace`, com o contêiner `totem-local-builder`. A aquisição inicial exige internet; a compilação subsequente para esta configuração usa os arquivos em cache. Mantenha espaço livre no Mac para os builds.

ZMK fixado em `7823a43f627e5a14fc92238783480d52ae5ed1ce`; a imagem de compilação está fixada por digest em `build.py`. Não executamos reset dos vínculos Bluetooth. Os dados de teclas e saída ficam apenas em memória; não são gravados em um histórico de digitação.

## Verificar

```sh
python3 -m unittest discover -s local
node --check local/static/app.js
python3 local/build.py left
python3 local/build.py right
```

Execute os comandos a partir da pasta `TOTEM-Local`. `native/build-app.command` recompila o aplicativo nativo com as Command Line Tools da Apple.
