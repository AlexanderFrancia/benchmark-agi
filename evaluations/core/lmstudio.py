import json
import re
import time
import requests
from django.conf import settings

class LMStudioError(Exception):
    pass

def list_models():
    """
    GET {LMSTUDIO_BASE_URL}/models
    Retorna el JSON completo que expone LM Studio (OpenAI-compatible).
    """
    url = f"{settings.LMSTUDIO_BASE_URL.rstrip('/')}/models"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise LMStudioError(str(e)) from e


def chat_completion(model: str, messages: list, temperature: float = 0.0, max_tokens: int = 2048):
    print("chat_completion called")
    """
    1) Intenta /v1/chat/completions (modelos instruct/chat).
    2) Si 400 (o no soportado), reintenta /v1/completions con prompt concatenado.
    """
    base = settings.LMSTUDIO_BASE_URL.rstrip("/")
    print(f"LMStudio base URL: {base}") 
    # ---- 1) Chat completions
    chat_url = f"{base}/chat/completions"
    chat_payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    try:
        r = requests.post(chat_url, json=chat_payload, timeout=120)
        if r.status_code == 200:
            data = r.json()
            return data["choices"][0]["message"]["content"]
        else:
            # guarda texto de error para diagnóstico
            err_text = r.text
            # si es 400, probamos /completions como fallback
            if r.status_code == 400:
                # ---- 2) Fallback a completions (modelos base)
                prompt = messages_to_prompt(messages)
                comp_url = f"{base}/completions"
                comp_payload = {
                    "model": model,
                    "prompt": prompt,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False,
                }
                r2 = requests.post(comp_url, json=comp_payload, timeout=120)
                if r2.status_code == 200:
                    data2 = r2.json()
                    # algunos backends devuelven 'choices[0].text' en /completions
                    return data2["choices"][0].get("text") or data2["choices"][0]["message"]["content"]
                else:
                    raise LMStudioError(
                        f"/chat/completions devolvió {r.status_code} ({err_text}) y "
                        f"/completions devolvió {r2.status_code} ({r2.text})"
                    )
            else:
                raise LMStudioError(f"/chat/completions devolvió {r.status_code}: {err_text}")
    except requests.RequestException as e:
        raise LMStudioError(str(e))

def messages_to_prompt(messages):
    """
    Convierte mensajes chat a un prompt plano para /v1/completions.
    Marcamos roles para no perder instrucciones.
    """
    chunks = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        chunks.append(f"[{role.upper()}]\n{content}\n")
    chunks.append("[ASSISTANT]\n")  # señal para que continúe
    return "\n".join(chunks)



