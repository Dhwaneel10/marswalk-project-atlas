app_path = r"E:\Python\NASA-Spaceapps\Marswalk\web\app.js"
with open(app_path, "r", encoding="utf-8") as f:
    code = f.read()

code = code.replace("disruptionZoneMesh", "disruptionHazardMesh")
code = code.replace("detourRouteMesh", "detourRouteLineMesh")

with open(app_path, "w", encoding="utf-8") as f:
    f.write(code)

print("Fixed mesh variable names in web/app.js.")
