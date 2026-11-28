# VANTIS — Visual Identity Assets

Este pacote foi montado a partir da prancha de identidade visual enviada como referência.

## Importante
O símbolo foi **reconstruído como vetor editável aproximado** com base na imagem de referência. Não é o arquivo vetorial original do designer. A tipografia rasterizada nas versões PNG usa uma fonte de sistema; para produção final, recomenda-se substituir por uma família tipográfica licenciada e converter o lettering em curvas.

## Paleta
| Nome | HEX | Uso |
|---|---|---|
| Vantis Blue | #0052F5 | Cor primária |
| Cyber Cyan | #00CFE8 | Destaque / gradiente |
| Deep Space | #080E1A | Fundos escuros |
| Slate Gray | #1C202B | Superfícies |
| Pure White | #FFFFFF | Fundos claros / contraste |
| Neutral Gray | #AAB0BA | Texto secundário |

## Estrutura
- `branding/logo/`: logotipos horizontais, empilhados e monocromáticos.
- `branding/symbol/`: símbolo V isolado em SVG e PNG.
- `branding/favicon/`: ícones para aplicativo e favicon.
- `patterns/`: padrão geométrico SVG.
- `backgrounds/`: fundos visuais em alta resolução.
- `reference/`: prancha original enviada como referência.

## Regras de uso
1. Não distorcer nem alterar as proporções do símbolo.
2. Preferir SVG em interfaces web quando possível.
3. Usar a versão branca em fundos escuros e a versão escura em fundos claros.
4. Reservar o gradiente azul/ciano para o símbolo e pequenos destaques.
5. Manter contraste alto e evitar efeitos decorativos excessivos.

## Integração
Copie a pasta `features/` para o repositório VANTIS. Ajuste os caminhos de importação conforme a estrutura do frontend.
