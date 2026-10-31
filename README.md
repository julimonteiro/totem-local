# TOTEM Local

Um companheiro local para o teclado split [TOTEM](https://github.com/GEIGEIGEIST/TOTEM), com firmware ZMK, editor visual e painel flutuante nativo para macOS.

- Veja o mapa das 38 teclas enquanto usa outros aplicativos.
- Acompanhe bateria de cada metade, conexão, camada ativa e teclas pressionadas.
- Confira a saída HID gerada pelo ZMK, como `A`, `Shift` ou `⌘ C`.
- Edite teclas com controles simples e carregue cada metade por USB.
- Compile no seu computador, com backups e sem depender de GitHub Actions.

## Instalar em outro Mac

1. Baixe `TOTEM-Local-macOS-universal.zip` em [Releases](https://github.com/julimonteiro/totem-local/releases).
2. Descompacte, arraste **TOTEM Local.app** para Aplicativos e abra.

O aplicativo inclui Python e código para Apple Silicon e Intel. Requer macOS 13 ou posterior. Os dados ficam em `~/Library/Application Support/TOTEM Local`; não é preciso instalar Python para abrir o painel. A versão distribuída tem assinatura ad hoc, sem notarização da Apple; o macOS pode exigir autorização para abrir o aplicativo em Ajustes do Sistema → Privacidade e Segurança.

Para **compilar atualizações de firmware**, instale e inicie um ambiente Docker compatível, como Docker Desktop ou Colima com Docker CLI. O primeiro build baixa a toolchain e dependências; os próximos usam o cache local. O painel e o editor não precisam do Docker para abrir.

No menu **⌨ TOTEM**, marque ou desmarque **Painel flutuante** para mostrar ou ocultar o teclado. A opção acompanha o estado real da janela, inclusive depois de fechar pelo ×. O mesmo menu reabre o editor. O painel permanece sobre as janelas, não recebe o foco de digitação e mostra somente o controle de fechar. O editor mantém os controles normais de janela e um campo nativo para testar texto recebido pelo macOS.

## Mapa inicial simples

Três camadas, com letras QWERTY normais e sem funções diferentes ao tocar/segurar letras.

| Camada | Como acessar | Conteúdo |
|---|---|---|
| BASE | Sempre | Letras, pontuação e modificadores dedicados |
| NAV | Segure NAV, no polegar direito | Números, setas, símbolos e navegação |
| AJUSTES | Segure NAV e depois Esc | Perfis Bluetooth e seleção de saída |

Os seis polegares, da esquerda para a direita, são: **Control · Command · Espaço · Enter · NAV · Shift**. A tecla externa esquerda é Esc e a externa direita é Backspace. Alt/Option fica no lugar de Control ao segurar NAV. Segure Shift com um número para obter seus símbolos usuais.

Em AJUSTES, as cinco teclas superiores esquerdas escolhem os perfis Bluetooth 1–5. Na direita, as três primeiras selecionam USB, Bluetooth e alternância; a última limpa o vínculo do perfil atual. Essas ações exigem manter NAV + Esc, para reduzir acionamentos acidentais.

## Editar e carregar

Clique na tecla, escolha a ação e use **Aplicar à tecla**. **Salvar** escreve apenas no Mac e cria um backup. **Carregar no esquerdo/direito** compila se necessário e aguarda a metade escolhida entrar no bootloader com dois toques no RESET. A conclusão exige que o próprio firmware confirme a versão.

A **esquerda é a central** que envia a digitação ao computador. A direita sozinha em USB fornece energia e telemetria, mas não substitui a central.

O painel só mostra o mapa de uma versão de firmware conhecida. A saída exibida é o comando HID do ZMK; o texto e os acentos finais dependem do layout do macOS. Leituras antigas são sinalizadas como indisponíveis.

## Estado da versão inicial

Esta é uma versão **preview**, testada com hardware TOTEM/XIAO BLE por USB em Apple Silicon. A telemetria por USB, os builds e a confirmação de gravação foram exercitados. O bridge CoreBluetooth e a compilação Intel estão incluídos; a operação Bluetooth completa e a execução em Intel ainda precisam de validação em hardware. Não apresentamos a falha Bluetooth original como corrigida. Também há uma investigação de texto não aparecendo no aplicativo host apesar de eventos HID presentes no macOS.

## Desenvolvimento

O backend usa apenas a biblioteca padrão do Python. O fallback Bluetooth no editor aberto em navegador pode usar Bleak; o app nativo usa CoreBluetooth.

```sh
python3 -m unittest discover -s local
node --check local/static/app.js
python3 local/server.py
```

Para builds de firmware, com Docker ativo:

```sh
python3 local/build.py left
python3 local/build.py right
```

Para o app e o pacote universal, com as Command Line Tools da Apple e GitHub CLI:

```sh
native/build-app.command
python3 scripts/package-macos.py
```

A revisão do ZMK, a imagem Docker e os hashes dos runtimes Python são fixados. Veja [THIRD_PARTY.md](THIRD_PARTY.md) para os componentes e licenças. Dados de dispositivos, backups, logs, ambientes locais e artefatos de build não são publicados no repositório.
