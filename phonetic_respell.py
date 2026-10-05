"""
Bollywood phonetic respelling for F5-TTS
Longest-match-first, case-insensitive, whole-word replacement
"""
import re

RESPELL = {
    # ---------- Artists: singers, composers, lyricists ----------
    "Lata Mangeshkar": "Lutah Mungayshkur",
    "Asha Bhosle": "Ahshah Bohslay",
    "Kishore Kumar": "Kishohr Koomaar",
    "Mohammed Rafi": "Muhummud Rufee",
    "Mukesh": "Mookaysh",
    "Udit Narayan": "Oodit Naaraayun",
    "Kumar Sanu": "Koomaar Saanoo",
    "Alka Yagnik": "Ulkah Yaagnik",
    "Sonu Nigam": "Sohnoo Nigum",
    "Shreya Ghoshal": "Shrayah Ghohshaal",
    "Arijit Singh": "Ureejit Sing",
    "Atif Aslam": "Aatif Uslum",
    "Sunidhi Chauhan": "Soonidhee Chauhaan",
    "Neha Kakkar": "Nayhah Kukkur",
    "Jubin Nautiyal": "Joobin Nowtiyaal",
    "Rahat Fateh Ali Khan": "Rahut Futay Ullee Kahn",
    "Mika Singh": "Meekah Sing",
    "Badshah": "Baadshaah",
    "A R Rahman": "Ay Ar Rahmaan",
    "Pritam": "Preetum",
    "Shankar Ehsaan Loy": "Shunkur Ehsaan Loy",
    "Javed Akhtar": "Jaavayd Ukhtur",
    "Gulzar": "Goolzaar",
    "Anand Bakshi": "Aanund Bukshee",

    # ---------- Artists: actors and filmmakers ----------
    "Shah Rukh Khan": "Shah Rook Kahn",
    "Salman Khan": "Sulmaan Kahn",
    "Aamir Khan": "Aamir Kahn",
    "Amitabh Bachchan": "Umitaabh Buchchun",
    "Akshay Kumar": "Ukshay Koomaar",
    "Hrithik Roshan": "Rittik Rohshun",
    "Ranbir Kapoor": "Rumbeer Kapoor",
    "Ranveer Singh": "Runveer Sing",
    "Govinda": "Gohvindah",
    "Anil Kapoor": "Unil Kapoor",
    "Kajol": "Kaajol",
    "Madhuri Dixit": "Maadhuree Dikshit",
    "Sridevi": "Shreedayvee",
    "Rani Mukerji": "Raanee Mukerjee",
    "Preity Zinta": "Preetee Zintah",
    "Priyanka Chopra": "Preeyunkah Chopraa",
    "Deepika Padukone": "Deepikah Paadookohn",
    "Alia Bhatt": "Aaliyah Bhutt",
    "Katrina Kaif": "Kutreenah Kaif",
    "Anushka Sharma": "Unooshkah Sharmah",
    "Karan Johar": "Kurun Johar",
    "Aditya Chopra": "Uditya Chopraa",
    "Yash Chopra": "Yush Chopraa",

    # ---------- Films ----------
    "Dilwale Dulhania Le Jayenge": "Dilwahlay Dulhaniyah Lay Jaayengay",
    "DDLJ": "Dilwahlay Dulhaniyah Lay Jaayengay",
    "Dil To Pagal Hai": "Dil Toh Paagul Hai",
    "DTPH": "Dil Toh Paagul Hai",
    "Kuch Kuch Hota Hai": "Kutch Kutch Hohtah Hai",
    "KKHH": "Kutch Kutch Hohtah Hai",
    "Kabhi Khushi Kabhie Gham": "Kubbee Kushee Kubbee Gum",
    "K3G": "Kubbee Kushee Kubbee Gum",
    "Mohabbatein": "Mohubbutayn",
    "Rab Ne Bana Di Jodi": "Rub Nay Bunah Dee Johdee",
    "RNBDJ": "Rub Nay Bunah Dee Johdee",
    "Kabhi Alvida Naa Kehna": "Kubbee Ulvidah Nah Kaynah",
    "Kal Ho Naa Ho": "Kul Hoh Nah Hoh",
    "Dil Se": "Dil Say",
    "Veer Zaara": "Veer Zaarah",
    "Devdas": "Dayvdaas",
    "Om Shanti Om": "Ohm Shaantee Ohm",
    "Dil Chahta Hai": "Dil Chaahtah Hai",
    "Zindagi Na Milegi Dobara": "Zindugee Nah Milaygee Dohbaarah",
    "Yeh Jawaani Hai Deewani": "Yay Jawaanee Hai Deewaanee",
    "Hum Aapke Hain Koun": "Hum Aapkay Hain Kohn",
    "Maine Pyar Kiya": "Mainay Pyaar Kiyah",
    "Hum Dil De Chuke Sanam": "Hum Dil Day Chukay Sunum",
    "Dilwale": "Dilwahlay",
    "Baazigar": "Baazeegur",
    "Darr": "Durr",
    "Kaho Naa Pyaar Hai": "Kuhoh Nah Pyaar Hai",
    "Lagaan": "Lugaan",
    "Dangal": "Dungaal",
    "Sholay": "Shohlay",
    "Mughal E Azam": "Mughul Ay Uzum",
    "Swades": "Swaydays",
    "Taal": "Taahl",
    "Pardes": "Pardays",
    "Barfi": "Burfee",
    "Tamasha": "Tumaashaa",
    "Raanjhanaa": "Raanjhunaa",
    "Ae Dil Hai Mushkil": "Ay Dil Hai Mushkil",
    "Aashiqui 2": "Aashikee Two",
    "Aashiqui": "Aashikee",
    "3 Idiots": "Three Idiots",
    "Pathaan": "Pahthaan",
    "Jawan": "Jawaan",
    "Dabangg": "Dubungg",
    "Dil Hai Ki Manta Nahin": "Dil Hai Kee Maantah Nahin",
    "Raja Hindustani": "Raajah Hindoostaanee",
    "Jab Tak Hai Jaan": "Jub Tuk Hai Jaan",
    "Rehna Hai Tere Dil Mein": "Rayhnaa Hai Tayray Dil Mayn",

    # ---------- Songs ----------
    "Haule Haule": "Haulay Haulay",
    "Yeh Ladka Hai Deewana": "Yay Ludkah Hai Deewahnah",
    "Tum Hi Ho": "Tum Hee Hoh",
    "Chaiyya Chaiyya": "Chaiyyah Chaiyyah",
    "Tujhe Dekha To Yeh Jaana Sanam": "Tujhay Daykhah Toh Yeh Jaanah Sunum",
    "Channa Mereya": "Chunnah Mayrayah",
    "Kesariya": "Kaysureeyah",
    "Apna Bana Le": "Upnah Bunah Lay",
    "Raabta": "Raabtah",
    "Gerua": "Gayruah",
    "Tum Se Hi": "Tum Say Hee",
    "Agar Tum Saath Ho": "Ugur Tum Saath Hoh",
    "Pehla Nasha": "Payhlah Nushah",
    "Pehli Nazar Mein": "Payhlee Nuzur Mayn",
    "Tere Naam": "Tayray Naam",
    "Mere Haath Mein": "Mayray Haath Mayn",
    "Suraj Hua Maddham": "Sooraj Huaa Muddhum",
    "Bole Chudiyan": "Bohlay Chudiyaan",
    "Tere Bina": "Tayray Binaa",
    "Dil Diyan Gallan": "Dil Diyaan Gullaan",
    "Tera Ban Jaunga": "Tayraa Bun Jaoongaa",
    "Ae Watan": "Ay Watun",
    "Chaleya": "Chulayyah",
    "Bulleya": "Bullayyah",
    "Kun Faya Kun": "Koon Fuyaa Koon",
    "Tujh Mein Rab Dikhta Hai": "Tujh Mayn Rub Dikhtaa Hai",
    
    # Additional playlist songs
    "Mere Khwabon Mein": "Mayray Kwaabohn Mayn",
    "Zara Sa Jhoom Loon Main": "Zurah Saa Jhoom Loon Mayn",
    "Ho Gaya Hai Tujhko To Pyar Sajna": "Hoh Guyah Hai Tujhkoh Toh Pyaar Sujnah",
    "Tujhe Dekha To": "Tujhay Daykhah Toh",
    "Chaand Taare": "Chaand Taaray",
    "Choodi Baji Hai": "Choodee Baajee Hai",
    "Main Koi Aisa Geet Gaoon": "Mayn Koee Aysah Geet Gaaoon",
    "Bholi Si Surat": "Bhohlee See Soorut",
    "Pyar Kar": "Pyaar Kur",
    "Are Re Are": "Uray Ray Uray",
    "Dholna": "Dholnah",
    "Koi Mil Gaya": "Koee Mil Guyah",
    "Tujhe Yaad Na Meri Aayee": "Tujhay Yaad Nah Mayree Aayee",
    "Saajanji Ghar Aaye": "Saajunjee Ghur Aayay",
    "Ladki Badi Anjani Hai": "Ludkee Buddee Unjaanee Hai",
    "Kuch Kuch Hota Hai (Sad)": "Kutch Kutch Hohtah Hai, the sad version",
    "Chalte Chalte": "Chultay Chultay",
    "Aankhein Khuli": "Aankhayn Khulee",
    "Humko Humise Chura Lo": "Humkoh Humeesay Churaa Loh",
    "Zinda Rehti Hain Mohabbatein": "Zindah Rayhtee Hain Mohubbutayn",
    "Say Shava Shava": "Say Shaavaa Shaavaa",
    "Yeh Ladka Hai Allah": "Yay Ludkah Hai Ullah",
    "Deewana Hai Dekho": "Deewahnah Hai Daykhoh",
    "Phir Milenge Chalte Chalte": "Pheer Milayngay Chultay Chultay",
    "Dance Pe Chance": "Dance Pay Chance",

    # ---------- Common words ----------
    "Bollywood": "Bolleewood",
    "Mohabbat": "Mohubbut",
    "Ishq": "Ishk",
}

# Build regex: longest-match-first, whole-word boundaries, case-insensitive
_LOOKUP = {k.lower(): v for k, v in RESPELL.items()}
_PATTERN = re.compile(
    r"(?<!\w)(" + "|".join(
        re.escape(k) for k in sorted(RESPELL, key=len, reverse=True)
    ) + r")(?!\w)",
    flags=re.IGNORECASE,
)


def respell(text: str) -> str:
    """Apply phonetic respelling to text"""
    return _PATTERN.sub(lambda m: _LOOKUP[m.group(1).lower()], text)


# ---------- Number / frequency normalization ----------
# F5-TTS reads raw digits literally and inconsistently ("105.9" -> "one hundred 5 point 9",
# or "one oh five"). A radio host always says the frequency as "one oh five point nine".
# Code owns this - the LLM keeps writing "105.9", we spell it out before TTS.
_NUM_WORDS = {
    "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
    "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
    "10": "ten", "11": "eleven", "12": "twelve", "13": "thirteen",
    "14": "fourteen", "15": "fifteen", "16": "sixteen", "17": "seventeen",
    "18": "eighteen", "19": "nineteen", "20": "twenty",
}


def normalize_numbers(text: str) -> str:
    """Spell numbers the way a radio presenter actually says them.

    Mainly the station frequency: '105.9' / '105 point 9' / '105.9 FM'
    -> 'one o five point nine'. Also handles a few common on-air forms
    (decades, years). Safe & idempotent - already-spelled text passes through.
    """
    if not text:
        return text

    # --- Station frequency: 105.9 -> one o five point nine ---
    # Match "105.9", "105 point 9", "105point9", "105.9FM", "105 . 9"
    # NOTE: "o" (letter name) renders cleaner than "oh" in F5-TTS for Junior -
    # RLHF freq test: "one o five point nine" cleanest, "one oh five, point nine" 2nd.
    text = re.sub(
        r"\b105\s*(?:\.|point)\s*9\b",
        "one o five point nine",
        text, flags=re.IGNORECASE,
    )
    # Bare "105" used as the frequency (e.g. "on 105 tonight")
    text = re.sub(r"\b105\b", "one o five", text)

    # --- Decades: 90s -> nineties, 80s -> eighties ---
    _decades = {
        "50s": "fifties", "60s": "sixties", "70s": "seventies",
        "80s": "eighties", "90s": "nineties", "00s": "two thousands",
    }
    for d, w in _decades.items():
        text = re.sub(rf"\b{d}\b", w, text, flags=re.IGNORECASE)

    # --- Times: 8:15 -> eight fifteen (only simple HH:MM) ---
    def _min_word(mi: str) -> str:
        # Leading zero on minutes is spoken as "oh": 1:05 -> "one oh five"
        if len(mi) == 2 and mi[0] == "0":
            last = _NUM_WORDS.get(mi[1], mi[1])
            return f"oh {last}" if last != "zero" else "o'clock"
        n = int(mi)
        if n == 0:
            return "o'clock"
        if n < 20:
            return _NUM_WORDS[str(n)]
        if n < 60:
            tens = ["twenty", "thirty", "forty", "fifty"]
            t = tens[n // 10 - 2]
            r = n % 10
            return t if r == 0 else f"{t} {_NUM_WORDS[str(r)]}"
        return mi  # unknown -> leave digits

    def _time_repl(m):
        h = int(m.group(1))
        hw = _NUM_WORDS.get(str(h), str(h))
        mw = _min_word(m.group(2))
        if mw == "o'clock":
            return f"{hw} o'clock"
        return f"{hw} {mw}"
    text = re.sub(r"\b([0-9]{1,2}):([0-9]{2})\b", _time_repl, text)

    return text
