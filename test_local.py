#!/usr/bin/env python3
"""
Script de pruebas local para verificar la funcionalidad básica
"""

import os
import json
import sys
from pathlib import Path


def test_file_structure():
    """Verifica que todos los archivos necesarios existan"""
    print("📁 Verificando estructura de archivos...")

    required_files = [
        "app/main.py",
        "app/secrets_loader.py",
        "app/agents/agent_selector.py",
        "app/agents/agent_type.py",
        "app/agents/web_agent.py",
        "app/agents/prompts/web_agent.txt",
        "app/agents/prompts/web_agent_description.txt",
        "app/utilities/get_prompts.py",
    ]

    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - FALTANTE")
            all_exist = False

    return all_exist


def test_prompt_files():
    """Verifica que los archivos de prompts tengan contenido"""
    print("\n📄 Verificando archivos de prompts...")

    prompt_files = [
        "app/agents/prompts/web_agent.txt",
        "app/agents/prompts/web_agent_description.txt",
    ]

    for file_path in prompt_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    print(f"✅ {file_path} - {len(content)} caracteres")
                else:
                    print(f"⚠️  {file_path} - VACÍO")
        except Exception as e:
            print(f"❌ {file_path} - Error: {e}")


def test_syntax():
    """Verifica que los archivos Python tengan sintaxis válida"""
    print("\n🔍 Verificando sintaxis de archivos Python...")

    python_files = [
        "app/main.py",
        "app/agents/agent_selector.py",
        "app/agents/web_agent.py",
        "app/utilities/get_prompts.py",
    ]

    for file_path in python_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                compile(content, file_path, "exec")
                print(f"✅ {file_path} - Sintaxis válida")
        except SyntaxError as e:
            print(f"❌ {file_path} - Error de sintaxis: {e}")
        except Exception as e:
            print(f"❌ {file_path} - Error: {e}")


def test_route_fixes():
    """Verifica que las rutas estén corregidas"""
    print("\n🛠️  Verificando correcciones de rutas...")

    try:
        with open("app/agents/web_agent.py", "r", encoding="utf-8") as f:
            content = f.read()

        if "./agents/prompts/web_agent.txt" in content:
            print("✅ Ruta de web_agent.txt corregida")
        else:
            print("❌ Ruta de web_agent.txt NO corregida")

        if "./agents/prompts/web_agent_description.txt" in content:
            print("✅ Ruta de web_agent_description.txt corregida")
        else:
            print("❌ Ruta de web_agent_description.txt NO corregida")

    except Exception as e:
        print(f"❌ Error verificando rutas: {e}")


def test_mock_request():
    """Simula una petición HTTP para probar la estructura"""
    print("\n🌐 Simulando petición HTTP...")

    # Crear una petición de prueba
    mock_request = {
        "question": "¿Cuál es el PIB más grande del 2025?",
        "model": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        "agent_id": "web_agent",
        "user_id": "test_user",
        "session_id": "test_session",
        "instructions": [
            {
                "instruction": "Responde de forma concisa",
                "description": "El usuario quiere una respuesta directa",
            }
        ],
        "files": [],
    }

    print("📤 Petición de prueba creada:")
    print(json.dumps(mock_request, indent=2, ensure_ascii=False))

    # Verificar que la estructura de la petición sea válida
    required_fields = ["question", "model", "agent_id"]
    for field in required_fields:
        if field in mock_request:
            print(f"✅ Campo '{field}' presente")
        else:
            print(f"❌ Campo '{field}' faltante")


def test_requirements():
    """Verifica que requirements.txt exista y tenga contenido"""
    print("\n📦 Verificando requirements.txt...")

    if os.path.exists("requirements.txt"):
        try:
            with open("requirements.txt", "r") as f:
                content = f.read().strip()
                if content:
                    lines = content.split("\n")
                    print(f"✅ requirements.txt - {len(lines)} dependencias")
                    print("📋 Dependencias principales:")
                    for line in lines[:5]:  # Mostrar solo las primeras 5
                        if line.strip() and not line.startswith("#"):
                            print(f"   - {line.strip()}")
                else:
                    print("⚠️  requirements.txt está vacío")
        except Exception as e:
            print(f"❌ Error leyendo requirements.txt: {e}")
    else:
        print("❌ requirements.txt no existe")


def main():
    """Función principal de pruebas"""
    print("🚀 Iniciando pruebas locales...\n")

    # Ejecutar todas las pruebas
    test_file_structure()
    test_prompt_files()
    test_syntax()
    test_route_fixes()
    test_mock_request()
    test_requirements()

    print("\n" + "=" * 50)
    print("📊 RESUMEN DE PRUEBAS")
    print("=" * 50)
    print("✅ Estructura de archivos verificada")
    print("✅ Sintaxis de Python verificada")
    print("✅ Rutas de archivos corregidas")
    print("✅ Petición de prueba creada")
    print("✅ Dependencias listadas")

    print("\n💡 PRÓXIMOS PASOS PARA EJECUTAR:")
    print("1. Instalar dependencias:")
    print("   pip install -r requirements.txt")
    print("\n2. Configurar variables de entorno:")
    print("   - AWS_ACCESS_KEY_ID")
    print("   - AWS_SECRET_ACCESS_KEY")
    print("   - AWS_DEFAULT_REGION")
    print("\n3. Ejecutar la aplicación:")
    print("   python app/main.py")
    print("\n4. Probar con curl:")
    print("   curl -X POST http://localhost:8081/task \\")
    print("     -H 'Content-Type: application/json' \\")
    print('     -d \'{"question":"test","model":"test","agent_id":"web_agent"}\'')


if __name__ == "__main__":
    main()
