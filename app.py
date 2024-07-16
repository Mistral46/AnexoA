import streamlit as st
import csv
import json
import pandas as pd
from pymongo import MongoClient
import matplotlib.pyplot as plt
from dotenv import load_dotenv
import os
from fpdf import FPDF

# Cargar variables de entorno desde .env
load_dotenv()

# Configurar MongoDB
mongo_uri = os.getenv("MONGODB_URI")
mongo_client = MongoClient(mongo_uri)
db = mongo_client["sgsi_db"]
collection = db["respuestas"]

# Opciones de estado y colores
status_options = ["Desconocido", "Inexistente", "Inicial", "Limitado", "Definido", "Gestionado", "Optimizado", "No Aplica"]
status_colors = {
    "Desconocido": "#D3D3D3",   # LightGray
    "Inexistente": "#FF6347",   # Tomato
    "Inicial": "#FFA500",       # Orange
    "Limitado": "#FFD700",      # Gold
    "Definido": "#ADFF2F",      # GreenYellow
    "Gestionado": "#32CD32",    # LimeGreen
    "Optimizado": "#4682B4",    # SteelBlue,
    "No Aplica": "#D3D3D3"      # LightGray
}

# Crear la barra lateral
st.sidebar.title("Status de un SGSI bajo norma ISO/IEC 27001:2022")
option = st.sidebar.radio("Selecciona una sección:", ["Introducción", "Requisitos obligatorios de la SgSi", "Controles del Anexo A", "Métricas"])

# Almacenar respuestas en caché
if "data" not in st.session_state:
    st.session_state.data = []

if "user_info" not in st.session_state:
    st.session_state.user_info = {"name": "", "company": "", "saved": False}

data = st.session_state.data
user_info = st.session_state.user_info

# Función para guardar respuestas en Excel
def save_to_excel(filename):
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)
    st.sidebar.success(f"Las respuestas han sido guardadas en {filename}")

# Función para guardar respuestas en MongoDB
def save_to_mongodb():
    if data:  # Verificar si data no está vacía
        document = {
            "user_info": user_info,
            "responses": data
        }
        collection.insert_one(document)
        st.sidebar.success("Las respuestas han sido guardadas en MongoDB")
    else:
        st.sidebar.error("No hay respuestas para guardar en MongoDB")

# Botones para guardar respuestas
if st.sidebar.button("Guardar en el equipo"):
    save_to_excel(f"{user_info['name']}_respuestas_sgsi.xlsx")
if st.sidebar.button("Guardar en MongoDB"):
    save_to_mongodb()

# Función para mostrar un selectbox con una etiqueta de referencia y colores personalizados
def labeled_selectbox(label, options, colors, key):
    selected_option = st.selectbox(f"**{label}**", options, key=key)
    st.markdown(f"""
    <style>
    .stSelectbox div[role="listbox"] > div[role="option"]:nth-child({options.index(selected_option) + 1}) {{
        background-color: {colors[selected_option]} !important;
    }}
    </style>
    """, unsafe_allow_html=True)
    # Actualizar el estado en los datos y autoguardar
    updated = False
    for entry in data:
        if entry["control"] == key:
            entry["status"] = selected_option
            updated = True
            break
    if not updated:
        data.append({"control": key, "status": selected_option})
    return selected_option

# Función para actualizar y mostrar gráficos
def show_charts(data):
    status_count = {status: 0 for status in status_options}
    for item in data:
        status_count[item["status"]] += 1

    labels = list(status_count.keys())
    sizes = list(status_count.values())
    colors = [status_colors[label] for label in labels]

    # Evitar errores de división por cero y NaN
    if sum(sizes) == 0:
        st.write("No hay datos para mostrar en el gráfico.")
    else:
        fig, ax = plt.subplots()
        ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
        ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
        ax.set_title("Status de Implementación SGSI")  # Título del gráfico
        st.pyplot(fig)

# Función para mostrar la tabla de métricas
def show_metrics_table(data):
    total_requisitos = len([item for item in data if item["control"].startswith("4.") or item["control"].startswith("5.") or item["control"].startswith("6.") or item["control"].startswith("7.") or item["control"].startswith("8.") or item["control"].startswith("9.") or item["control"].startswith("10.")])
    total_controles = len([item for item in data if item["control"].startswith("A.")])

    metrics_data = {
        "Status": ["Desconocido", "Inexistente", "Inicial", "Limitado", "Definido", "Gestionado", "Optimizado", "No Aplica"],
        "Significado": [
            "No ha sido siquiera revisado aún",
            "Ausencia completa de una política, procedimiento, control, etc legibles",
            "El desarrollo apenas ha comenzado y requerirá un trabajo significativo para satisfacer los requisitos",
            "Progresando bien pero no completado aún",
            "El desarrollo está más o menos completo aunque con ausencia de detalles y/o no está aún implementado, en cumplimiento vigente ni activamente avalado por la alta dirección.",
            "El desarrollo está completo, el proceso / control ha sido implementado y recientemente comenzó a operar",
            "El requisito está plenamente conforme, está plenamente operativo como se espera, está siendo activamente supervisado y mejorado, y hay evidencia sustancial para demostrar todo lo antedicho a los auditores",
            "TODOS los requerimientos en el cuerpo principal de la norma ISO/IEC 27001 son obligatorios SI su SGSI va a ser certificado. Caso contrario, la gerencia a cargo, puede ignorarlos"
        ],
        "Proporción de Requisitos del SGSI": [],
        "Proporción de Controles de Seguridad de la Información": []
    }

    for status in metrics_data["Status"]:
        count_requisitos = len([item for item in data if item["status"] == status and (item["control"].startswith("4.") or item["control"].startswith("5.") or item["control"].startswith("6.") or item["control"].startswith("7.") or item["control"].startswith("8.") or item["control"].startswith("9.") or item["control"].startswith("10."))])
        count_controles = len([item for item in data if item["status"] == status and item["control"].startswith("A.")])
        proportion_requisitos = (count_requisitos / total_requisitos) * 100 if total_requisitos else 0
        proportion_controles = (count_controles / total_controles) * 100 if total_controles else 0
        metrics_data["Proporción de Requisitos del SGSI"].append(f"{proportion_requisitos:.1f}%")
        metrics_data["Proporción de Controles de Seguridad de la Información"].append(f"{proportion_controles:.1f}%")

    df_metrics = pd.DataFrame(metrics_data)
    st.table(df_metrics)

# Función para generar el PDF
def generate_pdf(data, user_info, chart, table):
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Reporte SGSI - {user_info['company']}", ln=True, align="C")

    pdf.cell(200, 10, txt=f"Nombre: {user_info['name']}", ln=True, align="L")
    pdf.cell(200, 10, txt=f"Empresa: {user_info['company']}", ln=True, align="L")

    pdf.cell(200, 10, txt="Requisitos obligatorios de la SgSi", ln=True, align="L")

    for titulo, subtitulos in requisitos:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt=titulo, ln=True, align="L")
        for subtitulo, items in subtitulos:
            pdf.set_font("Arial", 'I', 12)
            pdf.cell(200, 10, txt=subtitulo, ln=True, align="L")
            for item in items:
                pdf.set_font("Arial", size=12)
                status = next((entry["status"] for entry in data if entry["control"] == item), "Desconocido")
                pdf.cell(200, 10, txt=f"{item}: {status}", ln=True, align="L")

    pdf.cell(200, 10, txt="Controles del Anexo A", ln=True, align="L")

    for titulo, items in controles:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt=titulo, ln=True, align="L")
        for item in items:
            pdf.set_font("Arial", size=12)
            status = next((entry["status"] for entry in data if entry["control"] == item), "Desconocido")
            pdf.cell(200, 10, txt=f"{item}: {status}", ln=True, align="L")

    # Agregar gráficos y tablas
    pdf.cell(200, 10, txt="Métricas", ln=True, align="L")
    pdf.image(chart, x=10, y=None, w=190)
    pdf.cell(200, 10, txt=table, ln=True, align="L")

    return pdf.output(dest="S").encode("latin1")

# Solicitar información del usuario
if option == "Introducción":
    st.title("Introducción")
    st.write("""Bienvenido al Sistema de Gestión de Seguridad de la Información (SGSI) según la norma ISO/IEC 27001.
             Esta aplicación se usa para registrar y hacer seguimiento del status de su organización a medida que implementa
              los elementos obligatorios y discrecionales de la norma ISO/IEC 27001. El cuerpo principal de la ISO/IEC 27001 
             especifica formalmente un número de requisitos obligarios que deben cumplirse con el objeto de que un SGSI 
             o Sistema de Gestión de la Seguridad de la Información sea certificado bajo la norma. Todos los requisitos 
             obligatorios para la certificación son relativos al sistema de gestión más que a los riesgos de la información 
             y a los controles de seguridad que sean aplicados. Por ejemplo, la norma requiere que la dirección determine 
             los riesgos de seguridad de la información de la organización, realizar una apreciación y valoración de los mismos,
              decidir cómo dichos riesgos serán tratados, tratarlos y supervisarlos, utilizando las políticas y procedimientos definidos en el SGSI. 
             La norma no obliga a emplear controles de seguridad específicos: es la organización la que los determina.""")
    st.write("Por favor, ingresa tu nombre y la empresa para continuar.")

    user_info["name"] = st.text_input("Nombre", value=user_info["name"])
    user_info["company"] = st.text_input("Empresa", value=user_info["company"])

    if st.button("Guardar y continuar"):
        if user_info["name"] and user_info["company"]:
            st.session_state.user_info["saved"] = True
            filename = f"{user_info['name']}_respuestas_sgsi.xlsx"
            save_to_excel(filename)
            st.sidebar.success(f"Información guardada y respuestas almacenadas en {filename}")
        else:
            st.sidebar.error("Por favor, completa todos los campos.")

elif not user_info["saved"]:
    st.title("Introducción")
    st.write("Por favor, ingresa tu nombre y la empresa para continuar en la sección de Introducción.")
    user_info["name"] = st.text_input("Nombre", value=user_info["name"])
    user_info["company"] = st.text_input("Empresa", value=user_info["company"])

    if st.button("Guardar y continuar"):
        if user_info["name"] and user_info["company"]:
            st.session_state.user_info["saved"] = True
            filename = f"{user_info['name']}_respuestas_sgsi.xlsx"
            save_to_excel(filename)
            st.sidebar.success(f"Información guardada y respuestas almacenadas en {filename}")
        else:
            st.sidebar.error("Por favor, completa todos los campos.")

else:
    filename = f"{user_info['name']}_respuestas_sgsi.xlsx"
    # Definir el contenido para cada sección
    if option == "Requisitos obligatorios de la SgSi":
        st.title("Requisitos obligatorios de la SgSi")

        # Datos de requisitos
        requisitos = [
            ("4 Contexto de la organización", [
                ("4.1 Contexto organizacional", [
                    "4.1 Determinar los objetivos del SGSI de la organización y cualquier cuestión que pueda comprometer su efectividad"
                ]),
                ("4.2 Partes interesadas", [
                    "4.2 (a) Identificar las partes interesadas incluyendo leyes aplicables, regulaciones, contratos, etc.",
                    "4.2 (b) Determinar sus requisitos relevantes al respecto de la seguridad de la información y sus obligaciones"
                ]),
                ("4.3 Alcance del SGSI", [
                    "4.3 Determinar y documentar el alcance del SGSI"
                ]),
                ("4.4 SGSI", [
                    "4.4 Establecer, implementar, mantener y mejorar continuamente un SGSI de conformidad con la norma"
                ]),
            ]),
            ("5 Liderazgo", [
                ("5.1 Liderazgo & compromiso", [
                    "5.1 La alta dirección debe demostrar liderazgo & compromiso en relación con el SGSI"
                ]),
                ("5.2 Política", [
                    "5.2 Establecer la política de seguridad de la información"
                ]),
                ("5.3 Roles, responsabilidades & autoridades en la organización", [
                    "5.3 Asignar y comunicar los roles & responsabilidades de la seguridad de la información"
                ]),
            ]),
            ("6 Planificación", [
                ("6.1 Acciones para tratar con los riesgos & oportunidades", [
                    "6.1.1 Diseñar / planificar el SGSI para satisfacer los requisitos, tratando con los riesgos & oportunidades",
                    "6.1.2 Definir y aplicar un proceso de apreciación de riesgos de seguridad de la información",
                    "6.1.3 Documentar y aplicar un proceso de tratamiento de riesgos de seguridad de la información"
                ]),
                ("6.2 Objetivos & planes de seguridad de la información", [
                    "6.2 Establecer y documentar los objetivos y planes de seguridad de la información"
                ]),
                ("6.3 Planificación de cambios", [
                    "6.3 Los cambios sustanciales al SGSI deben ser llevados a cabo de manera planificada"
                ]),
            ]),
            ("7 Soporte", [
                ("7.1 Recursos", [
                    "7.1 Determinar y proporcionar los recursos necesarios para el SGSI"
                ]),
                ("7.2 Competencias", [
                    "7.2 Determinar, documentar y poner a disposición las competencias necesarias"
                ]),
                ("7.3 Concientización", [
                    "7.3 Establecer un programa de concientización en seguridad"
                ]),
                ("7.4 Comunicación", [
                    "7.4 Determinar la necesidad para las comunicaciones internas y externas relevantes al SGSI"
                ]),
                ("7.5 Información documentada", [
                    "7.5.1 Proveer la documentación requerida por la norma así como la requerida por la organización",
                    "7.5.2 Proveer títulos, autores, etc para la documentación, adecuar el formato consistentemente, revisarlos & aprobarlos",
                    "7.5.3 Controlar la documentación adecuadamente"
                ]),
            ]),
            ("8 Operación", [
                ("8.1 Planificación y control operacional", [
                    "8.1 Planificar, implementar, controlar & documentar el proceso del SGSI para gestionar los riesgos (i.e. un plan de tratamiento de riesgos)"
                ]),
                ("8.2 Apreciación del riesgo de seguridad de la información", [
                    "8.2 (Re)hacer la apreciación & documentar los riesgos de seguridad de la información en forma regular & ante cambios o modificaciones"
                ]),
                ("8.3 Tratamiento del riesgo de seguridad de la información", [
                    "8.3 Implementar el plan de tratamiento de riesgos (tratar los riesgos!) y documentar los resultados"
                ]),
            ]),
            ("9 Evaluación del desempeño", [
                ("9.1 Seguimiento, medición, análisis y evaluación", [
                    "9.1 Hacer seguimiento, medir, analizar y evaluar el SGSI y los controles"
                ]),
                ("9.2 Auditoría interna", [
                    "9.2 Planificar y llevar a cabo auditorias internas del SGSI"
                ]),
                ("9.3 Revisión por la dirección", [
                    "9.3 Emprender revisiones por la dirección del SGSI regularmente"
                ]),
            ]),
            ("10 Mejora", [
                ("10.1 Mejora continua", [
                    "10.1 Mejorar continuamente el SGSI"
                ]),
                ("10.2 No conformidad y acciones correctivas", [
                    "10.2 Identificar, corregir y llevar a cabo acciones para prevenir la recurrencia de no conformidades, documentando las acciones"
                ]),
            ]),
        ]

        for titulo, subtitulos in requisitos:
            st.subheader(titulo)
            for subtitulo, items in subtitulos:
                st.write(f"**{subtitulo}**")
                for item in items:
                    st.write(item)
                    labeled_selectbox("Status", status_options, status_colors, key=item)

    elif option == "Controles del Anexo A":
        st.title("Controles del Anexo A")

        # Datos de controles
        controles = [
            ("A5 Controles organizacionales", [
                "A.5.1 Políticas para la seguridad de la información",
                "A.5.2 Roles y responsabilidades en la seguridad de la información",
                "A.5.3 Segregación de tareas",
                "A.5.4 Responsabilidades de gestión",
                "A.5.5 Contacto con las autoridades",
                "A.5.6 Contacto con grupos de interés especial",
                "A.5.7 Inteligencia de amenazas",
                "A.5.8 Seguridad de la información en la gestión de proyectos",
                "A.5.9 Inventario de activos de información y otros asociados a la misma",
                "A.5.10 Uso aceptable de activos de información y otros asociados a la misma",
                "A.5.11 Devolución de activos",
                "A.5.12 Clasificación de la información",
                "A.5.13 Etiquetado de la información",
                "A.5.14 Intercambio de la información",
                "A.5.15 Control de Acceso",
                "A.5.16 Gestión de la identidad",
                "A.5.17 Información de autenticación",
                "A.5.18 Derechos de acceso",
                "A.5.19 Seguridad de la información en la relación con proveedores",
                "A.5.20 Requisitos de seguridad de la información en contratos con terceros",
                "A.5.21 Gestión de la seguridad de la información en la cadena de suministro de las TIC (Tecnologías de Información y Comunicación)",
                "A.5.22 Gestión del cambio, revisión y monitoreo de los servicios del proveedor o suministrador",
                "A.5.23 Seguridad de la información para el uso de servicios en la nube (cloud)",
                "A.5.24 Planeamiento y preparación de la gestión de incidentes de seguridad de la información",
                "A.5.25 Evaluación y decisión en los eventos de seguridad de la información",
                "A.5.26 Respuesta a los incidentes de seguridad de la información",
                "A.5.27 Aprendizaje sobre los incidentes de seguridad de la información",
                "A.5.28 Recolección de evidencia",
                "A.5.29 Seguridad de la información durante interrupciones",
                "A.5.30 Preparación de las TIC para la continuidad de negocio",
                "A.5.31 Requisitos legales, estatutarios, regulatorios y contractuales",
                "A.5.32 Derechos de propiedad intelectual",
                "A.5.33 Protección de registros",
                "A.5.34 Privacidad y protección de la PII (Información Identificable Personal)",
                "A.5.35 Revisión independiente de la seguridad de la información",
                "A.5.36 Cumplimiento con las políticas, reglas y normas de la seguridad de la información",
                "A.5.37 Procedimientos operacionales documentados"
            ]),
            ("A6 Controles personales", [
                "A.6.1 Revisión de antecedentes",
                "A.6.2 Términos y condiciones de empleo",
                "A.6.3 Concientización, educación y entrenamiento en seguridad de la información",
                "A.6.4 Proceso disciplinario",
                "A.6.5 Responsabilidades luego de la finalización o cambio de empleo",
                "A.6.6 Acuerdos de confidencialidad o no revelación",
                "A.6.7 Trabajo remoto",
                "A.6.8 Reportes de eventos de seguridad de la información"
            ]),
            ("A7 Controles físicos", [
                "A.7.1 Perímetros de seguridad física",
                "A.7.2 Entrada física",
                "A.7.3 Seguridad de oficinas, despachos e instalaciones",
                "A.7.4 Supervisión de la seguridad física",
                "A.7.5 Protección contra amenazas físicas y ambientales",
                "A.7.6 Trabajo en áreas seguras",
                "A.7.7 Escritorio y pantalla limpios",
                "A.7.8 Emplazamiento y protección de equipos",
                "A.7.9 Seguridad de activos fuera de las instalaciones",
                "A.7.10 Medios de almacenamiento",
                "A.7.11 Servicios de suministro",
                "A.7.12 Seguridad del cableado",
                "A.7.13 Mantenimiento de equipos",
                "A.7.14 Eliminación o re utilización segura de equipos"
            ]),
            ("A8 Controles tecnológicos", [
                "A.8.1 Dispositivos terminales de usuario",
                "A.8.2 Derechos de acceso privilegiado",
                "A.8.3 Restricción de acceso a la información",
                "A.8.4 Acceso al código fuente",
                "A.8.5 Autenticación segura",
                "A.8.6 Gestión de la capacidad",
                "A.8.7 Protección contra código malicioso (malware)",
                "A.8.8 Gestión de vulnerabilidades técnicas",
                "A.8.9 Gestión de la configuración",
                "A.8.10 Borrado de información",
                "A.8.11 Enmascarado de datos",
                "A.8.12 Prevención de filtración de datos",
                "A.8.13 Respaldo de información",
                "A.8.14 Redundancia de las instalaciones de procesamiento de información",
                "A.8.15 Registración",
                "A.8.16 Actividades de supervisión",
                "A.8.17 Sincronización de reloj (clock)",
                "A.8.18 Uso de programas utilitarios privilegiados",
                "A.8.19 Instalación de software en sistemas operacionales",
                "A.8.20 Seguridad en redes",
                "A.8.21 Seguridad de servicios de red",
                "A.8.22 Segregación de redes",
                "A.8.23 Filtrado web",
                "A.8.24 Uso de criptografía",
                "A.8.25 Desarrollo seguro del ciclo de vida",
                "A.8.26 Requerimientos de seguridad en aplicaciones",
                "A.8.27 Principios de arquitectura de sistemas e ingeniería seguras",
                "A.8.28 Generación de código seguro",
                "A.8.29 Prueba segura en el desarrollo y aceptación",
                "A.8.30 Desarrollo tercerizado",
                "A.8.31 Separación de entornos de desarrollo, prueba y producción",
                "A.8.32 Gestión de cambios",
                "A.8.33 Información de prueba",
                "A.8.34 Protección de sistemas de información durante pruebas de auditoría"
            ])
        ]

        for titulo, items in controles:
            st.subheader(titulo)
            for item in items:
                st.write(item)
                labeled_selectbox("Status", status_options, status_colors, key=item)

    elif option == "Métricas":
        st.title("Métricas")
        # Mostrar gráficos
        show_charts(data)
        # Mostrar tabla de métricas
        show_metrics_table(data)
