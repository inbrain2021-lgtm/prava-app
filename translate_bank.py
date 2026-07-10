"""
KOROAD savollar bankini O'zbek tiliga tarjima qiluvchi skript.
Railway Console'da ishga tushiriladi:  python translate_bank.py
- ANTHROPIC_API_KEY va BOT_TOKEN env'dan olinadi (Railway'da allaqachon bor)
- Natija (bank_uz.json) Telegram orqali adminga fayl qilib yuboriladi
- O'chirib-yoqilsa davom etadi (progress saqlanadi)
"""
import json, os, time, urllib.request

API_KEY = "".join(os.getenv("ANTHROPIC_API_KEY", "").split())
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = 1885197959
BATCH = 8          # bir so'rovda nechta savol
MODEL = "claude-haiku-4-5-20251001"
SRC = "bank_ko_priority.json"
OUT = "bank_uz.json"

def call_claude(prompt):
    body = json.dumps({"model": MODEL, "max_tokens": 4000,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": API_KEY, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read())
    return data["content"][0]["text"]

def translate_batch(batch):
    src = [{"num": q["num"], "q": q["question_ko"], "opts": q["options_ko"],
            "expl": q["explanation_ko"][:300]} for q in batch]
    prompt = (
        "Sen Koreya haydovchilik imtihoni savollarini O'zbek tiliga tarjima qiluvchi mutaxassissan.\n"
        "Quyidagi savollarni tarjima qil. Texnik atamalarni aniq tarjima qil "
        "(어린이 보호구역=bolalar himoya zonasi, 안전거리=xavfsiz masofa, 서행=sekin yurish).\n"
        "Koreyscha atamalarni kerak joyda qavsda saqla.\n\n"
        f"SAVOLLAR (JSON):\n{json.dumps(src, ensure_ascii=False)}\n\n"
        "Har savol uchun JSON qaytar (FAQAT json massiv, boshqa hech narsa):\n"
        '[{"num": N, "q_uz": "...", "opts_uz": ["...", ...], "expl_uz": "..."}]\n'
        "opts_uz soni asl opts soniga teng bo'lsin."
    )
    reply = call_claude(prompt).replace("```json", "").replace("```", "").strip()
    return json.loads(reply)

def send_file_to_admin(path, caption):
    if not BOT_TOKEN:
        return
    import subprocess
    subprocess.run(["curl", "-s", "-F", f"chat_id={ADMIN_ID}",
                    "-F", f"document=@{path}", "-F", f"caption={caption}",
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"],
                   capture_output=True)

def main():
    qs = json.load(open(SRC, encoding="utf-8"))
    done = {}
    if os.path.exists(OUT):
        for item in json.load(open(OUT, encoding="utf-8")):
            done[item["num"]] = item
        print(f"Davom etilmoqda: {len(done)} ta tayyor")
    todo = [q for q in qs if q["num"] not in done]
    print(f"Tarjima qilinadi: {len(todo)} / {len(qs)}")
    for i in range(0, len(todo), BATCH):
        batch = todo[i:i+BATCH]
        try:
            results = translate_batch(batch)
            for r in results:
                src_q = next(q for q in qs if q["num"] == r["num"])
                done[r["num"]] = {
                    "num": r["num"], "category": src_q["category"], "points": src_q["points"],
                    "question_ko": src_q["question_ko"], "question_uz": r["q_uz"],
                    "options_ko": src_q["options_ko"], "options_uz": r["opts_uz"],
                    "answers": src_q["answers"],
                    "explanation_uz": r.get("expl_uz", ""),
                }
            json.dump(sorted(done.values(), key=lambda x: x["num"]),
                      open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print(f"✅ {len(done)}/{len(qs)} tayyor (oxirgi: {batch[-1]['num']})")
        except Exception as e:
            print(f"⚠️ Xato ({batch[0]['num']}-{batch[-1]['num']}): {e} — 15s kutib davom")
            time.sleep(15)
        time.sleep(1.5)
    print("🎉 TUGADI!")
    send_file_to_admin(OUT, f"✅ Tarjima tayyor: {len(done)} savol")

if __name__ == "__main__":
    main()
