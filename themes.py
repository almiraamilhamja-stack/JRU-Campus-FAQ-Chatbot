"""Appearance themes for the JRU Campus FAQ Chatbot.

Each theme is a set of CSS variables. styles.css uses only these variables, so every page and component
(sidebar, header, cards, buttons, chat bubbles, inputs, tables, navigation) follows the selected theme."""

# variable -> meaning
#   heading/text/muted: text colours         brand: dark fill (user chat bubble)      accent/accent2: highlight colour (+ lighter)
#   on_accent: text on the accent colour     page/card/border: backgrounds and lines   soft/soft2: pale accent fills
#   chip: chip border                        sb1/sb2: sidebar gradient                 sb_text/sb_muted: sidebar text
#   sb_act1/sb_act2/sb_act_text: active menu item   sb_hover: hover fill               input: form field background
_BASE_KEYS = ("heading", "text", "muted", "brand", "brand_text", "accent", "accent2", "on_accent", "page", "card", "border",
              "soft", "soft2", "chip", "sb1", "sb2", "sb_text", "sb_muted", "sb_rule", "sb_act1", "sb_act2", "sb_act_text",
              "sb_hover", "input", "shadow", "scheme")

THEMES = {
    "navy_gold": {
        "name": "JRU Navy & Gold", "desc": "Navy blue, gold, cream and white (default).",
        "heading": "#102B4E", "text": "#263445", "muted": "#4A5870", "brand": "#102B4E", "brand_text": "#FFFFFF",
        "accent": "#D4A843", "accent2": "#E8C468", "on_accent": "#0B1F38", "page": "#F8F6F0", "card": "#FFFFFF",
        "border": "#ECE6D3", "soft": "#FBF0CF", "soft2": "#FFF8E4", "chip": "#E6CF8C", "sb1": "#102B4E", "sb2": "#0B1F38",
        "sb_text": "#FFFFFF", "sb_muted": "#AEB9D0", "sb_rule": "rgba(255,255,255,.16)", "sb_act1": "#E8C468", "sb_act2": "#D4A843",
        "sb_act_text": "#102B4E", "sb_hover": "rgba(255,255,255,.09)", "input": "#FFFFFF", "shadow": "rgba(16,43,78,.10)", "scheme": "light"},
    "light": {
        "name": "Light Mode", "desc": "Clean white and light gray with blue accents.",
        "heading": "#1F2937", "text": "#1F2937", "muted": "#5B6472", "brand": "#2563EB", "brand_text": "#FFFFFF",
        "accent": "#2563EB", "accent2": "#3B82F6", "on_accent": "#FFFFFF", "page": "#F1F3F5", "card": "#FFFFFF",
        "border": "#E1E5EB", "soft": "#E6EEFD", "soft2": "#EFF4FE", "chip": "#BFD1F7", "sb1": "#FFFFFF", "sb2": "#F7F8FA",
        "sb_text": "#1F2937", "sb_muted": "#5B6472", "sb_rule": "#E1E5EB", "sb_act1": "#3B82F6", "sb_act2": "#2563EB",
        "sb_act_text": "#FFFFFF", "sb_hover": "#EAEFF8", "input": "#FFFFFF", "shadow": "rgba(31,41,55,.10)", "scheme": "light"},
    "dark": {
        "name": "Dark Mode", "desc": "Dark background and sidebar with readable light text.",
        "heading": "#F2F5FA", "text": "#E6EAF2", "muted": "#A5B0C5", "brand": "#2F4A7C", "brand_text": "#FFFFFF",
        "accent": "#E0B84F", "accent2": "#EBCB78", "on_accent": "#101826", "page": "#0F1623", "card": "#182235",
        "border": "#2A3650", "soft": "#2A3350", "soft2": "#212B42", "chip": "#3A4A70", "sb1": "#0A101B", "sb2": "#0A101B",
        "sb_text": "#E6EAF2", "sb_muted": "#8F9BB3", "sb_rule": "rgba(255,255,255,.12)", "sb_act1": "#EBCB78", "sb_act2": "#E0B84F",
        "sb_act_text": "#101826", "sb_hover": "rgba(255,255,255,.08)", "input": "#1B2640", "shadow": "rgba(0,0,0,.45)", "scheme": "dark"},
    "forest": {
        "name": "Forest Green", "desc": "Green and cream, nature-inspired.",
        "heading": "#1F4D3A", "text": "#25362D", "muted": "#55695C", "brand": "#1F5F46", "brand_text": "#FFFFFF",
        "accent": "#3F8F63", "accent2": "#5BAA7E", "on_accent": "#FFFFFF", "page": "#F4F1E4", "card": "#FFFDF6",
        "border": "#DDD9C4", "soft": "#DDEBD9", "soft2": "#EAF2E4", "chip": "#B7D2B5", "sb1": "#1F4D3A", "sb2": "#163A2C",
        "sb_text": "#FFFFFF", "sb_muted": "#B9D3C4", "sb_rule": "rgba(255,255,255,.16)", "sb_act1": "#A8D8B9", "sb_act2": "#8CC9A0",
        "sb_act_text": "#163A2C", "sb_hover": "rgba(255,255,255,.09)", "input": "#FFFFFF", "shadow": "rgba(31,77,58,.12)", "scheme": "light"},
    "royal": {
        "name": "Royal Blue", "desc": "Professional blue and white.",
        "heading": "#14357A", "text": "#1E293B", "muted": "#526080", "brand": "#1E3A8A", "brand_text": "#FFFFFF",
        "accent": "#2F6FE4", "accent2": "#5B8DEF", "on_accent": "#FFFFFF", "page": "#F3F6FD", "card": "#FFFFFF",
        "border": "#DCE4F5", "soft": "#E3ECFD", "soft2": "#EEF3FE", "chip": "#B7CBF5", "sb1": "#1E3A8A", "sb2": "#14296B",
        "sb_text": "#FFFFFF", "sb_muted": "#B8C6EA", "sb_rule": "rgba(255,255,255,.18)", "sb_act1": "#FFFFFF", "sb_act2": "#E3ECFD",
        "sb_act_text": "#1E3A8A", "sb_hover": "rgba(255,255,255,.10)", "input": "#FFFFFF", "shadow": "rgba(30,58,138,.12)", "scheme": "light"},
    "warm": {
        "name": "Warm Neutral", "desc": "Beige, cream, brown and warm gray.",
        "heading": "#5A3E2B", "text": "#3E3229", "muted": "#6F6154", "brand": "#6B4A35", "brand_text": "#FFFFFF",
        "accent": "#B07D48", "accent2": "#C99562", "on_accent": "#FFFFFF", "page": "#F6EFE4", "card": "#FFFBF4",
        "border": "#E6D9C6", "soft": "#F0E2CC", "soft2": "#F8EEDD", "chip": "#D9BF98", "sb1": "#5A3E2B", "sb2": "#46301F",
        "sb_text": "#FFF6E8", "sb_muted": "#D9C7AE", "sb_rule": "rgba(255,255,255,.16)", "sb_act1": "#E8CC9D", "sb_act2": "#E3C08F",
        "sb_act_text": "#46301F", "sb_hover": "rgba(255,255,255,.09)", "input": "#FFFFFF", "shadow": "rgba(90,62,43,.12)", "scheme": "light"},
}
DEFAULT_THEME = "navy_gold"
FONT_SIZES = {"Small": "14px", "Medium": "16px", "Large": "18px", "Extra Large": "20px"}


def theme_css(key):
    """:root block with every variable of the theme (unknown keys fall back to the default theme)."""
    t = THEMES.get(key) or THEMES[DEFAULT_THEME]
    body = "".join(f"--{k.replace('_', '-')}:{t[k]};" for k in _BASE_KEYS)
    return f":root{{{body}color-scheme:{t['scheme']};}}"