# Assistência diária no TOTEM Local

## Objetivo e decisões existentes

O usuário está se adaptando a um TOTEM sem legendas. Aprovou como úteis seis ideias: busca de teclas e atalhos, painel por camada, treino adaptativo, alertas de bateria, perfis de layout e diagnóstico guiado. Esta proposta detalha esse conjunto antes da implementação. Manter o app macOS atual, SwiftUI/AppKit no painel e HTML local no editor, é decisão técnica do implementador. Não requer serviço externo nem alteração do firmware para estas funções.

## Busca “Como faço…?”

Uma ação no menu de barra superior abre a busca no editor, que aceita nomes como “copiar”, “print”, “arroba”, uma letra ou símbolo. Os resultados mostram teclas, modificadores e caminho para ativar a camada, iluminados em um mapa próprio. O painel flutuante continua sem capturar foco. A busca distingue mapa gravado reconhecido de mapa em edição e nunca apresenta alterações não gravadas como disponíveis no teclado.

O resolvedor começa com teclas simples, modificadores, atalhos macOS conhecidos e caminhos por camadas momentâneas `&mo`, incluindo NAV → AJUSTES. Funções personalizadas não resolvidas aparecem com sua função ZMK, sem instruções inventadas. Símbolos dependem da fonte de entrada do macOS: o app oferece uma seleção explícita do mapa de símbolos suportado e identifica essa escolha junto ao resultado; não promete deduzir caracteres apenas do código HID. Copiar/colar e outros comandos são instruções, nunca executados globalmente pela busca.

## Painel por camada

Disponibilizar os modos “Sempre visível”, “Automático por camada” e “Oculto” no menu da barra superior, persistidos localmente. No modo automático, uma camada acima da base com telemetria recente exibe o painel e o retorno à base agenda seu desaparecimento após cerca de 350 ms. Uma nova troca cancela o desaparecimento pendente. Perda de telemetria esconde o painel automático e não mantém uma camada antiga visível. Fechar o painel o deixa oculto até nova escolha explícita de modo. O modo sempre visível permanece disponível. O usuário escolheu automático como padrão. Preservar ausência de foco, compatibilidade com outros Spaces e botão de fechar.

## Treino adaptativo

Estender o tutorial existente com sessões curtas de prática e uma sequência recomendada a partir dos erros observados apenas no campo de treino. Salvar contagens agregadas por tecla esperada, acertos, erros e sessões; nunca salvar texto digitado nem observar conteúdo de outros aplicativos. Comparar alterações de entrada para não contar repetidamente um erro quando a pessoa usa Backspace. Separar métricas por identidade do mapa e permitir apagar o progresso. Mais erros elevam a frequência da tecla nas próximas sequências, mantendo variedade. Preservar o tutorial inicial e os avisos para layouts não suportados; não usar sucesso de telemetria como prova de texto recebido.

## Bateria

Alertas independentes para cada metade, apenas com leitura recente entre 0 e 100%. Limiar inicial de 20%, com novo aviso em 10%. Evitar avisos repetidos: rearmar após leitura acima de 25% e manter o estado entre reinícios. Bateria desconhecida ou telemetria antiga não significa zero. Disponibilizar ativação explícita de notificações e explicar a permissão do macOS; se não autorizadas, manter aviso dentro do app. Não inferir carregamento sem informação real do aparelho.

## Perfis locais

Salvar o keymap completo atual com nome, data e identificador local. Listar perfis, duplicar, renomear e excluir arquivos de perfil sem excluir o mapa ativo. Oferecer “Iniciante” como modelo conhecido e “Programação” como modelo conservador que preserva as letras e polegares do iniciante, facilitando símbolos e delimitadores nas camadas auxiliares. Usar prévia por tecla antes de aplicar qualquer modelo.

Aplicar perfil altera somente o arquivo local, com backup, validação, controle de versão por hash e bloqueio durante compilação/gravação. A ação de carregar cada metade continua explícita e separada. Restaurar um backup usa a mesma prévia e mecanismo. Exportar/importar keymap permite transferir perfis entre Macs; validar tamanho, estrutura e funções antes de aplicar. Não permitir caminhos fornecidos pelo cliente: os arquivos ficam em diretório fixo do workspace. Preservar macros e nós personalizados do arquivo completo. Não tentar mesclar perfis de estruturas incompatíveis tecla por tecla.

## Diagnóstico guiado

Uma tela apresenta cada metade, cabo detectado, canal de telemetria, saída selecionada USB/Bluetooth, versão de firmware, atualidade dos dados e última comunicação. Distinguir a saída selecionada de uma conexão HID comprovada. O teste de texto exige digitação em um campo próprio. Uma metade direita via USB não é apresentada como central HID autônoma.

Mostrar ações e instruções específicas: conectar a esquerda para texto via cabo, conferir saída selecionada, reconectar telemetria ou seguir o procedimento de pareamento. O procedimento Bluetooth descreve esquecer TOTEM no macOS, limpar o perfil ativo e emparelhar novamente; a combinação física é calculada pelo mapa reconhecido. Sem mapa reconhecido, não sugerir posições presumidas. Nunca limpar vínculos, alterar a saída ou atualizar firmware automaticamente.

## Interface e entrega

Manter linguagem simples em português, materiais e controles nativos onde já existem, sem ocupar mais espaço permanente no painel. Editor concentra busca, prática, perfis e diagnóstico; menu oferece acesso direto. Configurações e agregados ficam neste Mac. A implementação inclui testes dos caminhos de camada, concorrência e restauração de perfis, dados antigos de bateria, visibilidade automática e contagem de erros. Verificar o editor no navegador e compilar o app nativo antes de reabrir o app atualizado. Documentar limites de validação com hardware real.

Publicar código no repositório público já autorizado e preparar novo ZIP macOS depois das verificações. Não anunciar DMG nem notarização inexistentes. Não gravar novo firmware nem refazer pareamento para instalar estas melhorias.
