import json
import os

import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

CATEGORY_LABELS = {
    "ia": "INTELIGÊNCIA ARTIFICIAL",
    "big-techs": "BIG TECHS",
    "ciberseguranca": "CIBERSEGURANÇA",
    "mercado-tech": "MERCADO TECH",
    "ciencia": "CIÊNCIA E TECH",
}


MAX_PICK_CANDIDATES = 30
MIN_SUMMARY_CHARS = 300


def pick_most_engaging(candidates: list[dict]) -> dict:
    """Escolhe, entre notícias REAIS já coletadas, a que mais prende o público brasileiro.

    Só escolhe — não altera nem inventa nada. Os vídeos que funcionaram no canal
    foram os práticos/curiosos (IA que liga por você, "esse vídeo é IA?"); os de
    bastidor corporativo (evento, investimento, benchmark) ficaram com 0-5 views.
    """
    # Resumo de 1 frase não sustenta gancho→tensão→recompensa sem inventar; só usa se não houver outra
    detailed = [c for c in candidates if len(c["summary"]) >= MIN_SUMMARY_CHARS]
    pool = (detailed or candidates)[:MAX_PICK_CANDIDATES]
    listing = "\n".join(
        f"{i}. [{c['source']}] {c['title']} — {c['summary'][:200]}" for i, c in enumerate(pool)
    )
    prompt = f"""Você é o editor de pauta do canal "Brasil Digital" (YouTube Shorts de tecnologia/IA para brasileiros comuns, no Brasil e nos EUA).

Escolha a notícia com MAIS potencial de prender a atenção, gerar comentários e compartilhamentos. Priorize o que afeta a vida da pessoa comum: celular, WhatsApp, Instagram, apps, golpes e segurança, dinheiro, emprego, saúde, IA que a pessoa pode usar, coisas chocantes ou curiosas que dão vontade de mandar pra alguém.
EVITE: eventos e ingressos, rodadas de investimento, valuation, briga de executivos, benchmark técnico, política interna de empresa, notícia que só interessa a quem trabalha no setor.
PROIBIDO: política partidária ou eleitoral (candidatos, partidos, eleições, governo vs. oposição) — mesmo que o assunto seja tecnologia, como deepfake de político.

Notícias:
{listing}

Responda APENAS com o número da notícia escolhida."""
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=10,
        messages=[{"role": "user", "content": prompt}],
    )
    idx = int("".join(ch for ch in response.content[0].text if ch.isdigit()))
    chosen = pool[idx]
    print(f"🎯 Pauta escolhida por engajamento ({idx} de {len(pool)} candidatas)")
    return chosen


def generate_content(article: dict) -> dict:
    """Transforma UMA notícia real (já coletada via RSS) em roteiro de Short.

    A regra inegociável: o modelo só pode usar o que está no texto da fonte.
    Nada de estatística, citação ou fato extra inventado ("achômetro" proibido).
    """
    prompt = f"""Você é o roteirista do canal "Brasil Digital" no YouTube — notícias REAIS de tecnologia contadas de um jeito que prende, pra brasileiro comum.

REGRA INEGOCIÁVEL: baseie-se EXCLUSIVAMENTE nas informações fornecidas abaixo, extraídas de uma matéria jornalística real. É PROIBIDO inventar números, datas, nomes, citações, causas ou consequências que não estejam no texto. Se um detalhe não estiver claro na fonte, seja mais genérico em vez de inventar — este é um canal de notícias verificadas, não de especulação ("zero achômetro").

Fonte: {article['source']}
Link original: {article['link']}
Título original (pode estar em inglês): {article['title']}
Resumo/trecho da matéria: {article['summary']}
Publicado: {article.get('published') or 'recentemente'}

Tarefa: adapte essa notícia real para um roteiro de YouTube Short vertical (~40-55 segundos) em português brasileiro. Tom de CONVERSA, como um amigo que entende de tecnologia contando uma novidade: frases curtas, fale com "você", explique o que isso muda na vida da pessoa. Nada de tom de telejornal nem jargão (se usar termo técnico, explique em 3 palavras). Pode ter emoção e surpresa, mas sem exagerar nem distorcer o fato.

GANCHO DOS PRIMEIROS 2 SEGUNDOS (crítico pro Short não ser pulado): identifique o detalhe MAIS surpreendente ou consequente da notícia — não o mais óbvio — e abra com ele em forma de afirmação de impacto ou pergunta direta. Isso é reordenar informação real, não inventar nada. Evite aberturas fracas e genéricas como "Nesta semana...", "Segundo uma nova pesquisa...", "A empresa X anunciou que..." — vá direto no fato que mais importa. O "hook" e a PRIMEIRA FRASE do "narration_script" devem transmitir esse mesmo gancho (podem usar palavras um pouco diferentes, mas o mesmo impacto), porque o espectador ouve a narração ao mesmo tempo em que vê o hook na tela.

ESTRUTURA EM 3 ATOS (gancho → tensão → recompensa), a que mais segura o público em Shorts:
1. GANCHO (1ª frase): o fato mais forte, que abre uma PERGUNTA na cabeça de quem assiste ("como assim?", "e agora?", "isso me afeta?"). Ação/consequência ANTES do contexto.
2. TENSÃO (~70% da narração): dê o contexto e os detalhes reais em ordem crescente de importância, SEM entregar ainda a resposta principal. Cada frase tem que dar um motivo pra continuar ouvindo (ex.: "Mas o detalhe que importa é outro.", "E é aí que fica sério."). Essas frases de transição só podem anunciar algo que de fato vem logo depois e está na fonte — nunca prometer o que a notícia não tem. Se parecer previsível, a pessoa pula. Não entregue a resposta principal nas 2 primeiras frases.
3. RECOMPENSA (penúltima parte, antes da pergunta final): entregue a resposta — o que isso significa na prática pra você, o desfecho, o "então é por isso". É o momento que faz o vídeo valer a pena e dá vontade de assistir de novo ou mandar pra alguém.
A recompensa também precisa estar NA FONTE. Se a matéria não diz a consequência, a recompensa é "o que se sabe até agora" — nunca suponha efeito no bolso/vida da pessoa. Processo, denúncia ou acusação continua sendo acusação no hook, no título, nos slides e na capa ("é acusado de", "processo diz que") — nunca afirme como fato.
Os slides seguem a mesma ordem: slide 1 = gancho, slides 2 e 3 = tensão, slide 4 = recompensa.

Responda APENAS com JSON válido, sem markdown, seguindo exatamente este formato:
{{
  "category": "uma destas categorias: ia, big-techs, ciberseguranca, mercado-tech, ciencia",
  "subject": "assunto principal em poucas palavras (ex: 'OpenAI', 'Nova lei de IA na UE')",
  "hook": "gancho de impacto com o fato mais surpreendente da notícia, afirmação forte ou pergunta direta (máx 90 caracteres) — não um resumo neutro",
  "slides": [
    {{"text": "slide 1 — manchete/hook (máx 80 caracteres)"}},
    {{"text": "slide 2 — tensão: contexto/fato que aumenta a curiosidade (máx 100 caracteres)"}},
    {{"text": "slide 3 — tensão: o detalhe que deixa mais sério (máx 100 caracteres)"}},
    {{"text": "slide 4 — recompensa: o que isso muda pra você (máx 100 caracteres)"}},
    {{"text": "Fonte: {article['source']}\\nBrasil Digital"}}
  ],
  "narration_script": "roteiro COMPLETO para narração em voz masculina séria, português brasileiro natural, 70 a 100 palavras (~45s falados), tom de conversa falando com 'você'. A PRIMEIRA FRASE precisa ser o mesmo gancho de impacto do campo 'hook' (mesmo fato surpreendente em destaque), depois vem a TENSÃO (contexto sem entregar a resposta) e então a RECOMPENSA (o que isso significa pra você). TERMINE com uma pergunta curta e direta pro espectador responder nos comentários, ligada ao tema (ex: 'Você usaria isso?', 'Você cairia nesse golpe?') e a ÚLTIMA frase é SEMPRE exatamente 'Segue o Brasil Digital.'. SEM inventar fatos além da fonte fornecida. SEM indicações de cena ou colchetes — só o texto narrado.",
  "youtube_title": "título que dá vontade de clicar (máx 70 caracteres): desperte curiosidade ou mostre o que a pessoa ganha/perde, pode falar com 'você', no máximo 1 emoji. Tem que ser 100% verdadeiro segundo a fonte — curiosidade sim, mentira ou exagero nunca. Evite títulos de manchete neutra tipo 'Empresa X anuncia Y'.",
  "youtube_description": "descrição com 2 parágrafos curtos resumindo a notícia + a mesma pergunta do final da narração convidando a comentar + uma linha 'Fonte: {article['source']} — {article['link']}' + 6 a 8 hashtags relevantes, sempre incluindo #BrasilDigital",
  "tags": ["tecnologia", "shorts", "...mais 8 tags relevantes ao tema específico da notícia"],
  "thumb_text": "texto GIGANTE da capa: 2 a 5 palavras de impacto em português, sem pontuação, verdadeiro segundo a fonte (ex: '15 SEGUNDOS DA SUA VOZ', 'O IPHONE QUE DOBRA', 'A IA INVADIU SOZINHA')",
  "badge": "selo vermelho curto, escolha UM: ALERTA, ALERTA DE GOLPE, URGENTE, NOVIDADE, CHOCANTE, VEJA ISSO, ATENÇÃO, LANÇAMENTO",
  "image_prompt": "descrição EM INGLÊS de uma cena fotográfica dramática que ilustre o tema pra capa (1-2 frases): pessoa comum anônima com emoção forte (surpresa, medo, alegria) ou objeto em destaque, luz de cinema. PROIBIDO: texto, logos, marcas, pessoas reais/famosas/executivos."
}}"""

    # O Haiku às vezes devolve JSON malformado (vírgula sobrando, aspas) — tenta de novo
    for tentativa in range(3):
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        try:
            content = json.loads(text.strip())
            break
        except json.JSONDecodeError as e:
            print(f"   ⚠️ JSON inválido (tentativa {tentativa + 1}/3): {e}")
            if tentativa == 2:
                raise

    content["source"] = article["source"]
    content["source_link"] = article["link"]
    if content.get("category") not in CATEGORY_LABELS:
        content["category"] = "ciencia"
    return content
