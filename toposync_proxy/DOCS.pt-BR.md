# TopoSync Remote Instance — Instância remota

[English setup](DOCS.md)

Este complemento instala **somente o acesso a uma instância TopoSync já instalada em outro lugar**. Processamento, câmeras, arquivos e atualizações permanecem nessa instância. Não é necessário instalar **TopoSync Full Application** junto dele. “Remota” também inclui outra máquina virtual no mesmo computador físico.

Para instalar a aplicação completa dentro do Home Assistant, escolha **TopoSync Full Application** na mesma loja.

## 1. Prepare a instância remota

Use uma versão do TopoSync que implemente o acesso autenticado em `/api/auth/ingress-proxy`. O complemento verifica esse suporte antes de encaminhar as requisições. Uma versão publicada antiga com o mesmo número não garante compatibilidade.

Antes de ativar a autenticação híbrida, acesse o TopoSync diretamente por uma conexão protegida e crie uma conta local proprietária. Ela permite recuperar o acesso quando o Home Assistant estiver indisponível. A criação inicial da conta pelo acesso direto fica desativada no modo híbrido.

Gere uma credencial dedicada em um computador confiável:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Trate o resultado como uma senha. Configure o processo ou contêiner remoto:

```yaml
environment:
  TOPOSYNC_AUTH_MODE: home_assistant_hybrid
  TOPOSYNC_AUTH_INGRESS_PROXY_TOKEN: "${TOPOSYNC_INGRESS_PROXY_TOKEN}"
  TOPOSYNC_AUTH_INGRESS_TRUSTED_IPS: "${TOPOSYNC_INGRESS_PROXY_SOURCE}"
  TOPOSYNC_STREAMING_HLS_PUBLIC_MODE: proxy
  FORWARDED_ALLOW_IPS: ""
```

Preencha `TOPOSYNC_INGRESS_PROXY_TOKEN` com a credencial gerada. Preencha `TOPOSYNC_INGRESS_PROXY_SOURCE` com o endereço de origem efetivamente visto pelo TopoSync: pode ser o Home Assistant, a passagem de rede do Docker ou outro proxy HTTPS. Use somente os endereços necessários, separados por vírgulas; `*` é rejeitado. A credencial continua obrigatória mesmo quando vários clientes compartilham esse endereço.

`FORWARDED_ALLOW_IPS: ""` mantém o endereço real da conexão na verificação. Se houver outro proxy HTTPS antes do TopoSync, ele deve encaminhar o domínio configurado para o servidor correto e preservar `X-Forwarded-Host`, `X-Forwarded-Proto`, `X-Ingress-Path`, `X-Toposync-Ingress-Token` e os três cabeçalhos `X-Remote-User-Id`, `X-Remote-User-Name` e `X-Remote-User-Display-Name`. Restrinja os pontos de acesso e não registre credenciais ou endereços de mídia assinados nos logs.

## 2. Instale e configure o complemento

Adicione `https://github.com/toposync/toposync-homeassistant-addon` aos repositórios da loja, instale **TopoSync Remote Instance** e abra **Configuração**.

| Campo | O que preencher |
| --- | --- |
| **Endereço da instância remota** (`server_url`) | Obrigatório. Exemplo: `https://toposync.example.com:8443`. Use somente a origem, sem usuário, senha, caminho, parâmetros ou fragmento. O TopoSync precisa estar servido em `/`. |
| **Credencial de acesso à instância remota** (`proxy_token`) | Obrigatório. A mesma credencial de `TOPOSYNC_AUTH_INGRESS_PROXY_TOKEN`, com 32–256 letras, números, sublinhados ou hífens. Não use o token do Home Assistant. |
| **Permitir HTTP por túnel privado criptografado** (`allow_http`) | Deixe desativado para exigir HTTPS válido. Ative somente quando um túnel privado existente proteger toda a conexão. Uma rede local comum não criptografa a credencial. |

Os dois campos obrigatórios começam vazios porque dependem da sua instalação. O endereço precisa ser acessível **a partir do complemento**. `localhost` aponta para o próprio contêiner, mesmo que as máquinas virtuais estejam no mesmo servidor físico.

O certificado HTTPS deve ser confiável pelas autoridades do sistema e corresponder ao nome do servidor. Esta versão não permite desativar essa verificação nem cadastrar uma autoridade própria.

Salve, inicie o complemento e selecione **Abrir interface web**. Ative **Mostrar na barra lateral** se desejar. A entrada será **TopoSync Remote Instance**. Os nomes da loja e da barra lateral permanecem em inglês; os campos acompanham o idioma do Home Assistant, e os erros de conexão acompanham o idioma principal do navegador. Há traduções em inglês e português brasileiro.

Não é necessário publicar portas. O acesso é restrito a administradores do Home Assistant; eles recebem o papel proprietário (`owner`) no TopoSync por padrão. Não há mapeamento individual de permissões nesta versão. O acesso direto ao TopoSync continua usando as contas locais.

## 3. Arquivos, vídeo e operação

Interface, arquivos, consultas, transmissões HLS, eventos contínuos e WebSockets passam pelo complemento. Uploads têm limite de 1 GiB; conexões de transmissão têm limite de uma hora sem atividade. Use HLS dentro do Home Assistant. RTSP e o transporte de mídia WebRTC exigem configuração de rede própria.

Parar, atualizar ou desinstalar este complemento não para o processamento remoto nem apaga seus dados. O backup do Home Assistant inclui as opções e a credencial do complemento, mas **não os dados remotos**. Proteja o backup e faça uma cópia independente dos dados da instância.

A extensão Home Assistant do TopoSync requer seu próprio endereço e credencial de API. Este complemento não exporta a credencial do Supervisor nem configura entidades, GPU, Samba ou servidores de mídia.

## Se não conectar

- **Acesso negado:** confira se as duas credenciais coincidem, se o endereço de origem está permitido e se o usuário atual é administrador. Entre novamente no Home Assistant e reabra o painel.
- **Conexão indisponível:** confira o endereço, a rede, a resolução do nome, o certificado e o suporte ao proxy autenticado no servidor. Corrija e recarregue a página.
- **Erro na inicialização:** o log indica o campo inválido e o formato esperado. Corrija em Configuração, salve e reinicie. As mensagens não mostram os valores das opções.

O complemento se recupera quando o servidor volta, sem precisar reiniciar. A resolução de nomes é renovada após 30 segundos. A verificação de saúde observa somente o proxy local, evitando reinícios repetidos quando o servidor está desligado. Logs de requisições e erros do Nginx ficam desativados para não expor credenciais ou endereços assinados.

Para trocar a credencial, altere o valor na instância remota e no complemento e reinicie os serviços afetados. O painel fica indisponível enquanto os valores forem diferentes; o acesso direto continua disponível.
