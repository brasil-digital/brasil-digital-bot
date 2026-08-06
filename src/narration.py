import os

from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# Voz masculina fixa e séria — identidade de "âncora" do canal, sem variar
# a cada vídeo (diferente do Ritmos do Brasil, que alterna vozes por variedade).
VOICE = "onyx"


def generate_narration(script: str, output_path: str = "/tmp/narration.mp3") -> str:
    print(f"🎙️  Gerando narração com voz '{VOICE}'...")

    response = client.audio.speech.create(
        model="tts-1-hd",
        voice=VOICE,
        input=script,
        response_format="mp3",
        speed=0.97,
    )

    with open(output_path, "wb") as f:
        f.write(response.content)
    print(f"✅ Áudio gerado: {output_path}")
    return output_path
