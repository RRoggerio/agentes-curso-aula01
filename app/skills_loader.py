# app/skills_loader.py
# Carrega Agent Skills (SKILL.md) com progressive disclosure.
# Nível 1: só metadados no boot. Nível 2: instruções sob demanda.

import os
import re
import glob


def parse_frontmatter(texto: str):
    """Separa o YAML frontmatter (name, description) do corpo markdown."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", texto, re.DOTALL)
    if not m:
        return {}, texto
    fm_raw, corpo = m.group(1), m.group(2)
    meta = {}
    for linha in fm_raw.splitlines():
        if ":" in linha:
            k, v = linha.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, corpo


def descobrir_skills(dir_skills="skills") -> dict:
    """NÍVEL 1: lê só os metadados (name + description) de cada skill."""
    skills = {}
    for caminho in glob.glob(os.path.join(dir_skills, "*", "SKILL.md")):
        meta, _ = parse_frontmatter(open(caminho, encoding="utf-8").read())
        if "name" in meta and "description" in meta:
            skills[meta["name"]] = {"description": meta["description"], "path": caminho}
    return skills


def carregar_skill(skills: dict, nome: str) -> str:
    """NÍVEL 2: carrega as instruções completas só quando a skill é escolhida."""
    _, corpo = parse_frontmatter(open(skills[nome]["path"], encoding="utf-8").read())
    return corpo


def resumo_para_prompt(skills: dict) -> str:
    """Monta o texto (nível 1) que vai ao system prompt do agente."""
    if not skills:
        return ""
    linhas = [f"- {nome}: {s['description']}" for nome, s in skills.items()]
    return "Você tem acesso às seguintes skills:\n" + "\n".join(linhas)
