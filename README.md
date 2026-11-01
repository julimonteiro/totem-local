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

No menu **⌨ TOTEM**, escolha **Automático por camada** (padrão), **Sempre visível** ou **Oculto**. No modo automático, o mapa aparece ao ativar uma camada e some cerca de 350 ms após voltar à base. Fechar pelo × mantém o painel oculto até você escolher novamente um modo no menu. O mesmo menu reabre o editor. O painel permanece sobre as janelas, não recebe o foco de digitação e mostra somente o controle de fechar. O editor mantém os controles normais de janela e um campo nativo para testar texto recebido pelo macOS.

## Tutorial de adaptação

No menu **⌨ TOTEM → Tutorial de adaptação**, ou pelo botão **Aprender a usar o split** no editor, abra o roteiro guiado de dez etapas. Ele cobre posição das mãos, F/J, letras, alcance das fileiras, polegares, Shift, NAV, setas e Command+A.

O mapa destaca a próxima tecla e os modificadores necessários. Os exercícios de texto só passam quando a sequência chega ao campo do macOS; os exercícios de posições/setas identificam explicitamente a leitura do firmware. É possível ler a próxima etapa sem praticar, sem marcá-la como concluída. O progresso é local e não contém o texto digitado. A prática guiada exige o mapa iniciante reconhecido, para evitar ensinar posições de um firmware diferente.

## Assistência no dia a dia

Abra **Como faço…?** no editor ou no menu **⌨ TOTEM**. As quatro abas reúnem:

- **Como faço…?**: procure `copiar`, `print`, `@`, letras ou funções ZMK. O mapa ilumina as teclas e informa o que segurar. A busca distingue o firmware reconhecido do arquivo salvo no editor. Para símbolos, escolha explicitamente **ABC / EUA** se essa for sua fonte de entrada do macOS; outras fontes ainda não têm tradução de símbolos.
- **Praticar**: sequências curtas dão mais atenção às letras com erros. Somente contagens de acertos/erros e sessões são guardadas neste Mac, separadas por mapa; o texto não é salvo. O treino adaptativo exige o mapa iniciante reconhecido. É possível apagar o progresso.
- **Meus layouts**: salve, duplique, renomeie, exclua e exporte perfis completos; importe `.keymap`, experimente os modelos Iniciante/Programação ou restaure backups. Veja a prévia e aplique com backup antes de carregar o teclado. O modelo Programação preserva letras/polegares e coloca delimitadores na fileira do meio de NAV.
- **Diagnóstico**: confira cabo, atualidade dos dados, firmware e bateria de cada metade, além de instruções de pareamento. Saída selecionada e comandos gerados não são tratados como prova de texto recebido.

Para avisos por metade, ative **⌨ TOTEM → Avisos de bateria** e autorize notificações no macOS. Há alertas em 20% e 10%, sem repetição até a carga superar 25%. Leituras antigas não geram alertas. Se a permissão estiver negada, o aviso atual continua disponível dentro do app.

Perfis são locais ao workspace e não são publicados no GitHub. Aplicar um perfil não grava firmware: use os botões de carregar cada metade quando quiser efetivar a mudança no teclado.

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

Esta é uma versão **preview**, exercitada com TOTEM/XIAO BLE em Apple Silicon. O usuário confirmou a digitação por Bluetooth após esquecer o dispositivo no macOS, limpar o perfil ativo no teclado e emparelhar novamente. A telemetria USB, os builds e a confirmação de gravação foram exercitados. O bridge CoreBluetooth está incluído, mas a telemetria completa sem cabo ainda não foi validada separadamente. Intel é compilado, sem teste em hardware Intel. Os novos fluxos têm testes de lógica e interface; a entrega não simula uma descarga real de bateria nem exige novo pareamento.

## Desenvolvimento

O backend usa apenas a biblioteca padrão do Python. O fallback Bluetooth no editor aberto em navegador pode usar Bleak; o app nativo usa CoreBluetooth.

```sh
python3 -m unittest discover -s local
node local/test_tutorial.cjs
node local/test_assistance.cjs
node --check local/static/assistance.js
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
