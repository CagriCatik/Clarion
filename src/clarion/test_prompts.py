from clarion.prompt_loader import render_prompt
import sys

try:
    print("Testing system_guidelines.j2...")
    sg = render_prompt("system_guidelines.j2")
    
    with open("debug_render.txt", "w", encoding="utf-8") as f:
        f.write(sg)

    if "Expert Technical Writer" not in sg:
        raise Exception("Persona missing in system_guidelines. See debug_render.txt")
    if "MERMAID DIAGRAM RULES" not in sg:
        raise Exception("Mermaid rules missing in system_guidelines")
    print("OK")

    print("Testing review.j2...")
    rv = render_prompt("review.j2", draft_content="TEST")
    if "Strict Technical Editor" not in rv:
        raise Exception("Persona editor missing in review")
    if "MERMAID DIAGRAM RULES" not in rv:
        raise Exception("Mermaid rules missing in review")
    print("OK")

    print("Testing json_enforcement.j2...")
    je = render_prompt("json_enforcement.j2", prompt="TEST", schema_json="{}")
    if "Do NOT include any explanatory text" not in je:
        raise Exception("JSON rules missing in json_enforcement")
    print("OK")

    print("Testing repair.j2...")
    rp = render_prompt("repair.j2", error="TEST")
    if "Do NOT include any explanatory text" not in rp:
        raise Exception("JSON rules missing in repair")
    print("OK")

    print("ALL TESTS PASSED")

except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1)
