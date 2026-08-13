import sys
import os
import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from datetime import datetime

# --- 1. CONFIGURACIÓN DE RUTAS PARA EL .EXE ---
def obtener_ruta(nombre_archivo):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, nombre_archivo)

NOMBRE_IMAGEN = obtener_ruta("tu_imagen.jpg")

# --- PALETA DE COLORES (TEMA GRIS & AZUL MARINO) ---
COLOR_BG_GRAY = "#e5e7eb"        # Fondo gris claro general
COLOR_PANEL = "#ffffff"          # Paneles blancos para contraste limpio
COLOR_INPUT = "#f3f4f6"          # Fondo gris sutil para los campos de texto
COLOR_TEXT_MAIN = "#1e293b"      # Texto principal pizarra oscuro
COLOR_TEXT_MUTED = "#64748b"     # Texto secundario / Reloj

COLOR_NAVY_DARK = "#0f172a"      # Azul marino profundo
COLOR_NAVY_MAIN = "#1e3a8a"      # Azul marino clásico institucional
COLOR_NAVY_LIGHT = "#2563eb"     # Azul brillante corporativo

# --- FUNCIÓN AUXILIAR PARA EL EFECTO HOVER EN BOTONES ---
def añadir_efecto_hover(boton, color_hover, color_normal):
    boton.bind("<Enter>", lambda e: boton.config(bg=color_hover))
    boton.bind("<Leave>", lambda e: boton.config(bg=color_normal))

# --- FUNCIÓN AUXILIAR DE VALIDACIÓN NUMÉRICA ---
def validar_solo_numeros(texto_propuesto):
    return texto_propuesto.isdigit() or texto_propuesto == ""

# --- 2. VERIFICACIÓN DE LIBRERÍAS EXTERNAS ---
try:
    from PIL import Image, ImageTk
    PIL_INSTALADO = True
except ImportError:
    PIL_INSTALADO = False

try:
    import pandas as pd
    PANDAS_INSTALADO = True
except ImportError:
    PANDAS_INSTALADO = False

# --- 3. MÓDULO DE BASE DE DATOS Y MIGRACIONES ---
def conectar_db():
    conn = sqlite3.connect("puertos_cantv.db")
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='switches'")
        fila_sql = cursor.fetchone()
        if fila_sql:
            sql_creacion = fila_sql[0].lower()
            if "unique" in sql_creacion and "nombre" in sql_creacion:
                cursor.execute("ALTER TABLE switches RENAME TO switches_viejos")
                cursor.execute("""
                    CREATE TABLE switches (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        num_switch TEXT,
                        nombre TEXT,
                        total_puertos TEXT
                    )
                """)
                cursor.execute("""
                    INSERT INTO switches (id, num_switch, nombre, total_puertos)
                    SELECT id, num_switch, nombre, total_puertos FROM switches_viejos
                """)
                cursor.execute("DROP TABLE switches_viejos")
                conn.commit()
    except Exception as e:
        print(f"Aviso en migración adaptativa: {e}")

    # Tabla de puertos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS puertos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT,
            ubicacion TEXT,
            rj45g TEXT,
            rj45a TEXT,
            switch TEXT,
            puerto TEXT,
            fecha_mod TEXT
        )
    """)
    
    # Tabla de switches definitiva
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS switches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            num_switch TEXT,
            nombre TEXT,
            total_puertos TEXT
        )
    """)

    # Tabla de usuarios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE,
            contrasena TEXT,
            pregunta TEXT,
            respuesta TEXT
        )
    """)
    
    # Semilla inicial admin
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE usuario = 'admin'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO usuarios (usuario, contrasena, pregunta, respuesta)
            VALUES ('admin', 'puertos2026', '¿Cuál es la palabra clave de recuperación?', 'cantv2026')
        """)
    
    # Migraciones complementarias seguras
    try:
        cursor.execute("ALTER TABLE puertos ADD COLUMN fecha_mod TEXT")
    except sqlite3.OperationalError: pass
    try:
        cursor.execute("ALTER TABLE puertos ADD COLUMN puerto TEXT")
    except sqlite3.OperationalError: pass
    try:
        cursor.execute("ALTER TABLE switches ADD COLUMN num_switch TEXT")
    except sqlite3.OperationalError: pass
        
    conn.commit()
    return conn

# Función encargada de cargar y filtrar datos en tiempo real
def cargar_datos(tabla, filtro_switch=None, busqueda=None):
    for i in tabla.get_children():
        tabla.delete(i)
    
    if filtro_switch is None:
        filtro_switch = var_filtro_switch.get() if 'var_filtro_switch' in globals() else "Todos"
    if busqueda is None:
        busqueda = var_busqueda.get() if 'var_busqueda' in globals() else ""

    conn = conectar_db()
    cursor = conn.cursor()
    
    query = "SELECT id, usuario, ubicacion, rj45g, rj45a, switch, puerto, fecha_mod FROM puertos WHERE 1=1"
    params = []
    
    if filtro_switch and filtro_switch != "Todos":
        query += " AND switch = ?"
        params.append(filtro_switch)
        
    if busqueda:
        query += " AND (usuario LIKE ? OR ubicacion LIKE ? OR rj45g LIKE ? OR rj45a LIKE ? OR puerto LIKE ? OR switch LIKE ?)"
        termino = f"%{busqueda}%"
        params.extend([termino, termino, termino, termino, termino, termino])
        
    cursor.execute(query, params)
    for fila in cursor.fetchall():
        tabla.insert("", tk.END, iid=fila[0], values=fila[1:])
    conn.close()

# Sincronizador automático de los filtros de la pantalla principal
def actualizar_combo_filtro_main():
    if 'combo_filtro_switch_widget' in globals() and combo_filtro_switch_widget.winfo_exists():
        try:
            conn = conectar_db()
            cursor = conn.cursor()
            cursor.execute("SELECT num_switch, nombre FROM switches")
            lista_switches = ["Todos", "Desconectado"] + [f"{fila[1]} (S/N: {fila[0]})" for fila in cursor.fetchall()]
            conn.close()
            combo_filtro_switch_widget['values'] = lista_switches
        except Exception:
            pass

# --- 4. MÓDULO DE INTERFAZ Y LÓGICA OPERACIONAL ---
def ordenar_columna(tabla, col, reverse):
    l = [(tabla.set(k, col), k) for k in tabla.get_children("")]
    try:
        l.sort(key=lambda t: float(t[0]), reverse=reverse)
    except ValueError:
        l.sort(reverse=reverse)
    for index, (val, k) in enumerate(l):
        tabla.move(k, "", index)
    tabla.heading(col, command=lambda: ordenar_columna(tabla, col, not reverse))

def exportar_a_excel():
    if not PANDAS_INSTALADO:
        messagebox.showerror("Error", "Debe instalar pandas y openpyxl para exportar (pip install pandas openpyxl)")
        return
    try:
        f_switch = var_filtro_switch.get() if 'var_filtro_switch' in globals() else "Todos"
        f_busqueda = var_busqueda.get() if 'var_busqueda' in globals() else ""
        
        conn = conectar_db()
        query = "SELECT usuario, ubicacion, rj45g, rj45a, switch, puerto, fecha_mod FROM puertos WHERE 1=1"
        params = []
        
        if f_switch and f_switch != "Todos":
            query += " AND switch = ?"
            params.append(f_switch)
            
        if f_busqueda:
            query += " AND (usuario LIKE ? OR ubicacion LIKE ? OR rj45g LIKE ? OR rj45a LIKE ? OR puerto LIKE ? OR switch LIKE ?)"
            termino = f"%{f_busqueda}%"
            params.extend([termino, termino, termino, termino, termino, termino])
            
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        if df.empty:
            messagebox.showwarning("Exportar", "No existen registros que coincidan con los filtros actuales para exportar.")
            return

        df.columns = ["USUARIO", "UBICACIÓN", "RJ-45 G", "RJ-45 A", "SWITCH", "PUERTO", "ÚLT. MODIFICACIÓN"]
        ruta_guardado = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Archivos de Excel", "*.xlsx")],
            title="Guardar reporte de puertos filtrados"
        )
        if ruta_guardado:
            df.to_excel(ruta_guardado, index=False)
            messagebox.showinfo("Éxito", f"Reporte filtrado exportado correctamente en:\n{ruta_guardado}")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo exportar el archivo: {e}")

def abrir_ventana_puerto(tabla, modo="añadir"):
    seleccion = tabla.selection()
    if modo == "modificar" and not seleccion:
        messagebox.showwarning("Modificar", "Seleccione un registro de la lista")
        return

    ventana_pop = tk.Toplevel(ventana)
    ventana_pop.title("Datos del Puerto")
    ventana_pop.geometry("320x560")
    ventana_pop.configure(bg=COLOR_BG_GRAY)
    ventana_pop.grab_set()

    if 'icono_global' in globals() and icono_global:
        ventana_pop.iconphoto(False, icono_global)

    validador_num = ventana_pop.register(validar_solo_numeros)

    campos = ["Usuario", "Ubicación", "RJ-45 G", "RJ-45 A", "Switch", "Puerto"]
    entradas = {}
    valores_actuales = tabla.item(seleccion[0])['values'] if modo == "modificar" else [""]*6

    for i, campo in enumerate(campos):
        texto_label = f"{campo}*" if campo in ["Switch", "Puerto"] else campo
        tk.Label(ventana_pop, text=texto_label, bg=COLOR_BG_GRAY, fg=COLOR_TEXT_MAIN, font=("Arial", 10, "bold")).pack(pady=(12, 0))
        
        if campo == "Switch":
            conn = conectar_db()
            cursor = conn.cursor()
            cursor.execute("SELECT num_switch, nombre FROM switches")
            # Adición de opción estática 'Desconectado' al inicio de las opciones elegibles
            lista_switches = ["Desconectado"] + [f"{fila[1]} (S/N: {fila[0]})" for fila in cursor.fetchall()]
            conn.close()
            
            en = ttk.Combobox(ventana_pop, values=lista_switches, width=28, state="readonly", font=("Arial", 10))
            if modo == "modificar" and i < len(valores_actuales):
                en.set(valores_actuales[i])
            en.pack(pady=4, ipady=2)
        else:
            en = tk.Entry(ventana_pop, width=30, bg=COLOR_PANEL, fg=COLOR_TEXT_MAIN, relief="solid", bd=1, font=("Arial", 10))
            if campo == "Puerto":
                en.config(validate="key", validatecommand=(validador_num, "%P"))
            if modo == "modificar" and i < len(valores_actuales):
                en.insert(0, valores_actuales[i])
            en.pack(pady=4, ipady=4)
            
        entradas[campo] = en

    def guardar():
        switch_sel = entradas["Switch"].get().strip()
        puerto_sel = entradas["Puerto"].get().strip()
        ubicacion_sel = entradas["Ubicación"].get().strip()

        if not switch_sel:
            messagebox.showerror("Campos Obligatorios", "El campo 'Switch' es obligatorio para guardar el registro.")
            return

        # El puerto sólo es estrictamente obligatorio si el Switch NO está "Desconectado"
        if switch_sel != "Desconectado" and not puerto_sel:
            messagebox.showerror("Campos Obligatorios", "El campo 'Puerto' es obligatorio para switches activos.")
            return

        conn = conectar_db()
        cursor = conn.cursor()

        # 1. VALIDACIÓN: Evitar Ubicaciones Duplicadas
        if ubicacion_sel:
            if modo == "añadir":
                cursor.execute("SELECT usuario, switch, puerto FROM puertos WHERE ubicacion = ?", (ubicacion_sel,))
            else:
                cursor.execute("SELECT usuario, switch, puerto FROM puertos WHERE ubicacion = ? AND id != ?", (ubicacion_sel, seleccion[0]))
            
            fila_dup_ubi = cursor.fetchone()
            if fila_dup_ubi:
                u_ocupante, sw_ocupante, pt_ocupante = fila_dup_ubi
                usuario_msg = u_ocupante if u_ocupante else "un usuario sin nombre"
                messagebox.showerror("Ubicación en Uso", 
                                     f"¡Conflicto de Inventario!\n\nLa ubicación '{ubicacion_sel}' ya está registrada.\n"
                                     f"Actualmente la utiliza: {usuario_msg}\n"
                                     f"En el equipo: {sw_ocupante} (Puerto: {pt_ocupante}).\n\n"
                                     "Cada puerto del inventario debe apuntar a una ubicación física única.")
                conn.close()
                return

        # VALIDACIONES MAESTRAS DE TELCO (Solo aplican si NO está en estado Desconectado)
        if switch_sel != "Desconectado":
            # 2. VALIDACIÓN: Capacidad física máxima basada en su Serial E
            if " (S/N: " in switch_sel:
                serial_extraido = switch_sel.split(" (S/N: ")[-1].rstrip(")")
                cursor.execute("SELECT total_puertos FROM switches WHERE num_switch = ?", (serial_extraido,))
            else:
                cursor.execute("SELECT total_puertos FROM switches WHERE nombre = ?", (switch_sel,))
                
            fila_sw = cursor.fetchone()
            
            if fila_sw:
                max_puertos = int(fila_sw[0])
                try:
                    num_puerto = int(puerto_sel)
                    if num_puerto > max_puertos or num_puerto <= 0:
                        messagebox.showerror("Límite de Puertos Excedido", 
                                             f"El switch seleccionado sólo posee {max_puertos} puertos físicos.\n\n"
                                             f"Por favor, ingrese un número de puerto válido entre 1 y {max_puertos}.")
                        conn.close()
                        return
                except ValueError:
                    messagebox.showerror("Error", "El número de puerto debe ser un valor numérico entero.")
                    conn.close()
                    return
            else:
                messagebox.showerror("Error", "El switch seleccionado no se encuentra en el inventario maestro.")
                conn.close()
                return

            # 3. VALIDACIÓN: Evitar duplicado de puertos físicos en uso en el mismo switch exacto
            if modo == "añadir":
                cursor.execute("SELECT usuario FROM puertos WHERE switch = ? AND puerto = ?", (switch_sel, puerto_sel))
            else:
                cursor.execute("SELECT usuario FROM puertos WHERE switch = ? AND puerto = ? AND id != ?", (switch_sel, puerto_sel, seleccion[0]))
            
            fila_duplicado = cursor.fetchone()
            if fila_duplicado:
                usuario_ocupante = fila_duplicado[0] if fila_duplicado[0] else "un usuario sin nombre asignado"
                messagebox.showerror("Puerto en Uso", 
                                     f"¡Conflicto de Red!\n\nEl puerto {puerto_sel} en el switch '{switch_sel}' ya se encuentra asignado.\n"
                                     f"Actualmente está ocupado por: {usuario_ocupante}.\n\n"
                                     "Por favor, seleccione un número de puerto que esté libre.")
                conn.close()
                return
        else:
            # Si se marca como desconectado y no se especifica puerto, se visualiza limpio
            if not puerto_sel:
                puerto_sel = "None"

        # Advertencia de campos vacíos secundarios
        campos_vacios = False
        for campo in campos:
            if campo not in ["Switch", "Puerto"] and not entradas[campo].get().strip():
                campos_vacios = True
                break
        
        if campos_vacios:
            respuesta = messagebox.askyesno("Campos vacíos", "¿Está seguro de dejar los demás campos (Usuario, Ubicación, etc.) en blanco?")
            if not respuesta:
                conn.close()
                return 

        ahora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        datos = (entradas["Usuario"].get(), ubicacion_sel, 
                 entradas["RJ-45 G"].get(), entradas["RJ-45 A"].get(), 
                 switch_sel, puerto_sel, ahora)

        if modo == "añadir":
            cursor.execute("""INSERT INTO puertos (usuario, ubicacion, rj45g, rj45a, switch, puerto, fecha_mod) 
                           VALUES (?, ?, ?, ?, ?, ?, ?)""", datos)
        else:
            cursor.execute("""UPDATE puertos SET usuario=?, ubicacion=?, rj45g=?, rj45a=?, switch=?, puerto=?, fecha_mod=? 
                           WHERE id=?""", datos + (seleccion[0],))
        
        conn.commit()
        conn.close()
        cargar_datos(tabla) 
        ventana_pop.destroy() 

    btn_g = tk.Button(ventana_pop, text="Guardar Cambios", bg=COLOR_NAVY_MAIN, fg="white", 
              activebackground=COLOR_NAVY_LIGHT, activeforeground="white",
              relief="flat", font=("Arial", 11, "bold"), width=20, command=guardar)
    btn_g.pack(pady=25)
    añadir_efecto_hover(btn_g, COLOR_NAVY_LIGHT, COLOR_NAVY_MAIN)

def borrar_puerto(tabla):
    seleccion = tabla.selection()
    if not seleccion:
        messagebox.showwarning("Borrar", "Seleccione un registro")
        return
    if messagebox.askyesno("Confirmar", "¿Eliminar permanentemente?"):
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM puertos WHERE id = ?", (seleccion[0],))
        conn.commit()
        conn.close()
        cargar_datos(tabla)

# --- VENTANA EMERGENTE: GESTIÓN DE SWITCHES ---
def abrir_ventana_switches():
    ventana_sw = tk.Toplevel(ventana)
    ventana_sw.title("Información y Configuración de Switches")
    ventana_sw.geometry("720x450")
    ventana_sw.configure(bg=COLOR_BG_GRAY)
    ventana_sw.grab_set()

    if 'icono_global' in globals() and icono_global:
        ventana_sw.iconphoto(False, icono_global)

    validador_num = ventana_sw.register(validar_solo_numeros)

    frame_izq = tk.Frame(ventana_sw, bg=COLOR_PANEL, padx=12, pady=12, relief="solid", bd=1)
    frame_izq.pack(side="left", fill="y", padx=10, pady=10)

    tk.Label(frame_izq, text="DATOS DEL SWITCH", font=("Arial", 10, "bold"), bg=COLOR_PANEL, fg=COLOR_TEXT_MAIN).pack(pady=(0, 10))
    
    tk.Label(frame_izq, text="Serial E*", bg=COLOR_PANEL, fg=COLOR_TEXT_MUTED, font=("Arial", 9, "bold")).pack(anchor="w", pady=(5,0))
    entry_num = tk.Entry(frame_izq, bg=COLOR_INPUT, fg=COLOR_TEXT_MAIN, relief="solid", bd=1, font=("Arial", 10), width=22)
    entry_num.pack(pady=4, ipady=3)

    tk.Label(frame_izq, text="Nombre / Modelo*", bg=COLOR_PANEL, fg=COLOR_TEXT_MUTED, font=("Arial", 9, "bold")).pack(anchor="w", pady=(5,0))
    entry_nom = tk.Entry(frame_izq, bg=COLOR_INPUT, fg=COLOR_TEXT_MAIN, relief="solid", bd=1, font=("Arial", 10), width=22)
    entry_nom.pack(pady=4, ipady=3)

    tk.Label(frame_izq, text="Cantidad de Puertos*", bg=COLOR_PANEL, fg=COLOR_TEXT_MUTED, font=("Arial", 9, "bold")).pack(anchor="w", pady=(5,0))
    entry_pts = tk.Entry(frame_izq, bg=COLOR_INPUT, fg=COLOR_TEXT_MAIN, relief="solid", bd=1, font=("Arial", 10), width=22, validate="key", validatecommand=(validador_num, "%P"))
    entry_pts.pack(pady=4, ipady=3)

    id_seleccionado = [None]

    def limpiar_campos():
        entry_num.delete(0, tk.END)
        entry_nom.delete(0, tk.END)
        entry_pts.delete(0, tk.END)
        id_seleccionado[0] = None

    def cargar_tabla_switches():
        for i in tabla_sw.get_children():
            tabla_sw.delete(i)
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, num_switch, nombre, total_puertos FROM switches")
        for fila in cursor.fetchall():
            tabla_sw.insert("", tk.END, iid=fila[0], values=fila[1:])
        conn.close()
        limpiar_campos()

    def guardar_switch():
        num = entry_num.get().strip()
        nom = entry_nom.get().strip()
        pts = entry_pts.get().strip()
        if not num or not nom or not pts:
            messagebox.showwarning("Campos obligatorios", "Por favor llene todos los campos.")
            return
        
        conn = conectar_db()
        cursor = conn.cursor()
        
        if id_seleccionado[0] is None:
            cursor.execute("SELECT id FROM switches WHERE num_switch = ?", (num,))
        else:
            cursor.execute("SELECT id FROM switches WHERE num_switch = ? AND id != ?", (num, id_seleccionado[0]))
            
        if cursor.fetchone():
            messagebox.showerror("Serial E Duplicado", f"El Serial E '{num}' ya está asignado a otro switch.")
            conn.close()
            return

        if id_seleccionado[0] is None:
            cursor.execute("INSERT INTO switches (num_switch, nombre, total_puertos) VALUES (?, ?, ?)", (num, nom, pts))
        else:
            cursor.execute("UPDATE switches SET num_switch=?, nombre=?, total_puertos=? WHERE id=?", (num, nom, pts, id_seleccionado[0]))
        
        conn.commit()
        conn.close()
        messagebox.showinfo("Éxito", "Datos de Switch guardados correctamente.")
        cargar_tabla_switches()
        actualizar_combo_filtro_main()

    def eliminar_switch():
        if id_seleccionado[0] is None:
            messagebox.showwarning("Eliminar", "Seleccione un switch de la lista lateral.")
            return
        if messagebox.askyesno("Confirmar", "¿Desea eliminar permanentemente este switch?"):
            conn = conectar_db()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM switches WHERE id=?", (id_seleccionado[0],))
            conn.commit()
            conn.close()
            cargar_tabla_switches()
            actualizar_combo_filtro_main()

    btn_save = tk.Button(frame_izq, text="Guardar / Actualizar", bg=COLOR_NAVY_MAIN, fg="white", font=("Arial", 10, "bold"), command=guardar_switch, width=18, relief="flat")
    btn_save.pack(pady=8, ipady=2)
    añadir_efecto_hover(btn_save, COLOR_NAVY_LIGHT, COLOR_NAVY_MAIN)

    btn_del = tk.Button(frame_izq, text="Eliminar Switch", bg="#b91c1c", fg="white", font=("Arial", 10, "bold"), command=eliminar_switch, width=18, relief="flat")
    btn_del.pack(pady=4, ipady=2)
    añadir_efecto_hover(btn_del, "#991b1b", "#b91c1c")

    btn_clean = tk.Button(frame_izq, text="Limpiar Formulario", bg="#4b5563", fg="white", font=("Arial", 9), command=limpiar_campos, width=18, relief="flat")
    btn_clean.pack(pady=12)
    añadir_efecto_hover(btn_clean, "#374151", "#4b5563")

    frame_der = tk.Frame(ventana_sw, bg=COLOR_BG_GRAY)
    frame_der.pack(side="right", fill="both", expand=True, padx=(0, 10), pady=10)

    columnas_sw = ("num", "nombre", "puertos")
    tabla_sw = ttk.Treeview(frame_der, columns=columnas_sw, show="headings")
    
    tabla_sw.heading("num", text="SERIAL E")
    tabla_sw.heading("nombre", text="SWITCH / MODELO")
    tabla_sw.heading("puertos", text="CANT. PUERTOS")
    
    tabla_sw.column("num", anchor="center", width=120)
    tabla_sw.column("nombre", anchor="center", width=180)
    tabla_sw.column("puertos", anchor="center", width=110)
    tabla_sw.pack(fill="both", expand=True)

    def al_seleccionar_fila(event):
        seleccion = tabla_sw.selection()
        if seleccion:
            id_seleccionado[0] = seleccion[0]
            valores = tabla_sw.item(seleccion[0])['values']
            entry_num.delete(0, tk.END)
            entry_num.insert(0, valores[0])
            entry_nom.delete(0, tk.END)
            entry_nom.insert(0, valores[1])
            entry_pts.delete(0, tk.END)
            entry_pts.insert(0, valores[2])

    tabla_sw.bind("<<TreeviewSelect>>", al_seleccionar_fila)
    cargar_tabla_switches()

# --- 5. MÓDULO DE VISTA PRINCIPAL (SISTEMA) ---
def mostrar_sistema():
    global var_filtro_switch, var_busqueda, combo_filtro_switch_widget
    
    ventana.state('zoomed') 
    ventana.resizable(True, True)
    ventana.configure(bg=COLOR_BG_GRAY)
    for widget in ventana.winfo_children(): widget.destroy()
    
    style = ttk.Style()
    style.theme_use("clam")
    
    style.configure("Treeview.Heading", background=COLOR_NAVY_MAIN, foreground="white", font=("Arial", 10, "bold"), borderwidth=0)
    style.map("Treeview.Heading", background=[('active', COLOR_NAVY_LIGHT)])
    
    style.configure("Treeview", background=COLOR_PANEL, fieldbackground=COLOR_PANEL, foreground=COLOR_TEXT_MAIN, rowheight=28, borderwidth=1, borderColor=COLOR_BG_GRAY)
    style.map("Treeview", background=[('selected', COLOR_NAVY_LIGHT)], foreground=[('selected', "white")])

    main_container = tk.Frame(ventana, bg=COLOR_BG_GRAY)
    main_container.pack(fill="both", expand=True, padx=15, pady=15)

    frame_acciones = tk.Frame(main_container, width=190, bg=COLOR_PANEL, relief="solid", bd=1)
    frame_acciones.pack(side="left", fill="y", padx=(0, 15))
    frame_acciones.pack_propagate(False)

    if 'icono_global' in globals() and icono_global:
        tk.Label(frame_acciones, image=imagen_sistema_tk, bg=COLOR_PANEL).pack(pady=(10, 5))
    else:
        tk.Label(frame_acciones, text="[ CANTV ]", bg=COLOR_INPUT, fg=COLOR_TEXT_MUTED, width=20, height=5, font=("Arial", 10, "bold")).pack(pady=(10, 5))

    var_filtro_switch = tk.StringVar(value="Todos")
    var_busqueda = tk.StringVar(value="")

    def ejecutar_filtrado_dinamico(*args):
        cargar_datos(tabla, var_filtro_switch.get(), var_busqueda.get())

    var_busqueda.trace_add("write", ejecutar_filtrado_dinamico)
    var_filtro_switch.trace_add("write", ejecutar_filtrado_dinamico)

    tk.Label(frame_acciones, text="🔍 BUSCAR TÉRMINO:", bg=COLOR_PANEL, fg=COLOR_TEXT_MUTED, font=("Arial", 8, "bold")).pack(anchor="w", padx=15, pady=(5, 0))
    entry_buscar = tk.Entry(frame_acciones, textvariable=var_busqueda, bg=COLOR_INPUT, fg=COLOR_TEXT_MAIN, relief="solid", bd=1, font=("Arial", 9))
    entry_buscar.pack(fill="x", padx=15, pady=(2, 6))

    tk.Label(frame_acciones, text="🎛️ FILTRAR SWITCH:", bg=COLOR_PANEL, fg=COLOR_TEXT_MUTED, font=("Arial", 8, "bold")).pack(anchor="w", padx=15, pady=(2, 0))
    
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT num_switch, nombre FROM switches")
    # Agregar "Desconectado" a las opciones de filtrado general
    lista_switches = ["Todos", "Desconectado"] + [f"{fila[1]} (S/N: {fila[0]})" for fila in cursor.fetchall()]
    conn.close()

    combo_filtro_switch_widget = ttk.Combobox(frame_acciones, textvariable=var_filtro_switch, values=lista_switches, state="readonly", font=("Arial", 9))
    combo_filtro_switch_widget.pack(fill="x", padx=15, pady=(2, 15))

    btn1 = tk.Button(frame_acciones, text="Añadir Puerto", bg=COLOR_NAVY_DARK, fg="white", activebackground=COLOR_NAVY_MAIN, activeforeground="white", relief="flat", font=("Arial", 10, "bold"), width=18, command=lambda: abrir_ventana_puerto(tabla, "añadir"))
    btn1.pack(pady=5, ipady=3)
    añadir_efecto_hover(btn1, COLOR_NAVY_MAIN, COLOR_NAVY_DARK)

    btn2 = tk.Button(frame_acciones, text="Modificar Puerto", bg=COLOR_NAVY_MAIN, fg="white", activebackground=COLOR_NAVY_LIGHT, activeforeground="white", relief="flat", font=("Arial", 10, "bold"), width=18, command=lambda: abrir_ventana_puerto(tabla, "modificar"))
    btn2.pack(pady=5, ipady=3)
    añadir_efecto_hover(btn2, COLOR_NAVY_LIGHT, COLOR_NAVY_MAIN)

    btn3 = tk.Button(frame_acciones, text="Eliminar Puerto", bg="#b91c1c", fg="white", activebackground=COLOR_NAVY_DARK, activeforeground="white", relief="flat", font=("Arial", 10, "bold"), width=18, command=lambda: borrar_puerto(tabla))
    btn3.pack(pady=5, ipady=3)
    añadir_efecto_hover(btn3, "#991b1b", "#b91c1c")

    btn4 = tk.Button(frame_acciones, text="Información Switches", bg=COLOR_NAVY_LIGHT, fg="white", activebackground=COLOR_NAVY_MAIN, activeforeground="white", relief="flat", font=("Arial", 10, "bold"), width=18, command=abrir_ventana_switches)
    btn4.pack(pady=5, ipady=3)
    añadir_efecto_hover(btn4, COLOR_NAVY_MAIN, COLOR_NAVY_LIGHT)

    btn5 = tk.Button(frame_acciones, text="Exportar a Excel", bg="#4b5563", fg="white", activebackground=COLOR_NAVY_MAIN, activeforeground="white", relief="flat", font=("Arial", 10, "bold"), width=18, command=exportar_a_excel)
    btn5.pack(pady=5, ipady=3)
    añadir_efecto_hover(btn5, "#374151", "#4b5563")

    tk.Label(frame_acciones, text="", bg=COLOR_PANEL).pack(expand=True)
    
    btn_close = tk.Button(frame_acciones, text="Cerrar Sistema", bg="#1e293b", fg="white", activebackground="#b91c1c", activeforeground="white", relief="flat", font=("Arial", 10, "bold"), width=18, command=ventana.quit)
    btn_close.pack(pady=5, ipady=2)
    añadir_efecto_hover(btn_close, "#0f172a", "#1e293b")

    label_reloj = tk.Label(frame_acciones, font=("Arial", 8), fg=COLOR_TEXT_MUTED, bg=COLOR_PANEL, justify="center")
    label_reloj.pack(pady=(2, 12))

    def actualizar_reloj():
        if label_reloj.winfo_exists(): 
            ahora = datetime.now()
            dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            dia_nombre = dias_semana[ahora.weekday()]
            texto_tiempo = f"{dia_nombre}\n{ahora.strftime('%d/%m/%Y')}\n{ahora.strftime('%H:%M:%S')}"
            label_reloj.config(text=texto_tiempo)
            ventana.after(1000, actualizar_reloj)

    actualizar_reloj() 

    frame_tabla = tk.Frame(main_container, bg=COLOR_BG_GRAY)
    frame_tabla.pack(side="right", fill="both", expand=True)

    columnas = ("usuario", "ubicacion", "rj45g", "rj45a", "switch", "puerto", "fecha")
    tabla = ttk.Treeview(frame_tabla, columns=columnas, show="headings")
    
    titulos = ["USUARIO", "UBICACIÓN", "RJ-45 G", "RJ-45 A", "SWITCH", "PUERTO", "ÚLT. MODIFICACIÓN"]
    
    for col, nombre in zip(columnas, titulos):
        tabla.heading(col, text=nombre, command=lambda _col=col: ordenar_columna(tabla, _col, False))
        if col == "switch":
            ancho = 260   
        elif col == "puerto":
            ancho = 90    
        elif col == "fecha":
            ancho = 160
        elif col == "usuario":
            ancho = 140
        else:
            ancho = 110
        tabla.column(col, anchor="center", width=ancho)

    tabla.pack(side="left", fill="both", expand=True)
    cargar_datos(tabla)

# --- 6. MÓDULO DE ACCESO Y RECUPERACIÓN ---
def validar_acceso():
    user = entry_user.get().strip()
    password = entry_pass.get().strip()
    
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE usuario=? AND contrasena=?", (user, password))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        mostrar_sistema()
    else:
        messagebox.showerror("Error", "Credenciales incorrectas")

def abrir_ventana_recuperacion():
    ventana_rec = tk.Toplevel(ventana)
    ventana_rec.title("Recuperar Contraseña")
    ventana_rec.geometry("340x420")
    ventana_rec.configure(bg=COLOR_BG_GRAY)
    ventana_rec.grab_set()
    ventana_rec.resizable(False, False)

    if 'icono_global' in globals() and icono_global:
        ventana_rec.iconphoto(False, icono_global)

    tk.Label(ventana_rec, text="RESTABLECER CREDENCIALES", font=("Arial", 11, "bold"), bg=COLOR_BG_GRAY, fg=COLOR_TEXT_MAIN).pack(pady=(20, 10))

    tk.Label(ventana_rec, text="Usuario*", font=("Arial", 9, "bold"), bg=COLOR_BG_GRAY, fg=COLOR_TEXT_MUTED).pack(pady=(5, 0))
    entry_rec_user = tk.Entry(ventana_rec, justify="center", bg=COLOR_PANEL, fg=COLOR_TEXT_MAIN, relief="solid", bd=1, font=("Arial", 10), width=24)
    entry_rec_user.pack(pady=4, ipady=3)

    tk.Label(ventana_rec, text="Pregunta de Seguridad:\n¿Cuál es la palabra clave de recuperación?", font=("Arial", 9, "bold"), bg=COLOR_BG_GRAY, fg=COLOR_TEXT_MUTED, justify="center").pack(pady=(10, 0))
    entry_rec_resp = tk.Entry(ventana_rec, justify="center", bg=COLOR_PANEL, fg=COLOR_TEXT_MAIN, relief="solid", bd=1, font=("Arial", 10), width=24)
    entry_rec_resp.pack(pady=4, ipady=3)

    tk.Label(ventana_rec, text="Nueva Contraseña*", font=("Arial", 9, "bold"), bg=COLOR_BG_GRAY, fg=COLOR_TEXT_MUTED).pack(pady=(10, 0))
    entry_rec_pass = tk.Entry(ventana_rec, show="*", justify="center", bg=COLOR_PANEL, fg=COLOR_TEXT_MAIN, relief="solid", bd=1, font=("Arial", 10), width=24)
    entry_rec_pass.pack(pady=4, ipady=3)

    def ejecutar_restablecimiento():
        user = entry_rec_user.get().strip()
        resp = entry_rec_resp.get().strip()
        nueva_pass = entry_rec_pass.get().strip()

        if not user or not resp or not nueva_pass:
            messagebox.showwarning("Campos vacíos", "Por favor, complete todos los campos.")
            return

        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT respuesta FROM usuarios WHERE usuario = ?", (user,))
        fila = cursor.fetchone()

        if fila:
            respuesta_correcta = fila[0]
            if resp.lower() == respuesta_correcta.lower():
                cursor.execute("UPDATE usuarios SET contrasena = ? WHERE usuario = ?", (nueva_pass, user))
                conn.commit()
                messagebox.showinfo("Éxito", "Contraseña restablecida correctamente.")
                ventana_rec.destroy()
            else:
                messagebox.showerror("Error", "La respuesta de seguridad es incorrecta.")
        else:
            messagebox.showerror("Error", "El usuario ingresado no existe.")
        
        conn.close()

    btn_reset = tk.Button(ventana_rec, text="RESTABLECER", command=ejecutar_restablecimiento, bg=COLOR_NAVY_MAIN, fg="white",
                          activebackground=COLOR_NAVY_LIGHT, activeforeground="white", relief="flat", font=("Arial", 10, "bold"), width=16)
    btn_reset.pack(pady=25, ipady=2)
    añadir_efecto_hover(btn_reset, COLOR_NAVY_LIGHT, COLOR_NAVY_MAIN)


# --- 7. CONFIGURACIÓN INICIAL DE VENTANA Y LOGIN ---
ventana = tk.Tk()
ventana.title("Acceso CANTV")
ventana.geometry("340x560") 
ventana.configure(bg=COLOR_BG_GRAY)
ventana.resizable(False, False)

# --- PREPARACIÓN DE IMÁGENES ---
icono_global = None
imagen_login_tk = None
imagen_sistema_tk = None

if PIL_INSTALADO and os.path.exists(NOMBRE_IMAGEN):
    try:
        img_original = Image.open(NOMBRE_IMAGEN)
        
        img_icon = img_original.resize((32, 32), Image.Resampling.LANCZOS)
        icono_global = ImageTk.PhotoImage(img_icon)
        ventana.iconphoto(False, icono_global) 
        
        img_login = img_original.resize((260, 180), Image.Resampling.LANCZOS)
        imagen_login_tk = ImageTk.PhotoImage(img_login)
        
        img_sistema = img_original.resize((160, 120), Image.Resampling.LANCZOS)
        imagen_sistema_tk = ImageTk.PhotoImage(img_sistema)
        
    except Exception as e:
        print(f"Aviso: No se pudo procesar la imagen: {e}")

# --- DISEÑO DE LOGIN ---
if imagen_login_tk:
    tk.Label(ventana, image=imagen_login_tk, bg=COLOR_BG_GRAY).pack(pady=(20, 10))
else:
    tk.Label(ventana, text="[ CANTV LOGO ]", font=("Arial", 12, "bold"), bg=COLOR_BG_GRAY, fg=COLOR_TEXT_MUTED).pack(pady=(40, 10))

tk.Label(ventana, text="SISTEMA DE GESTIÓN DE PUERTOS", font=("Arial", 11, "bold"), bg=COLOR_BG_GRAY, fg=COLOR_TEXT_MAIN).pack()

tk.Label(ventana, text="Usuario*", font=("Arial", 10, "bold"), bg=COLOR_BG_GRAY, fg=COLOR_TEXT_MUTED).pack(pady=(15, 0))
entry_user = tk.Entry(ventana, justify="center", bg=COLOR_PANEL, fg=COLOR_TEXT_MAIN, relief="solid", bd=1, font=("Arial", 11), width=22)
entry_user.pack(pady=4, ipady=4)

tk.Label(ventana, text="Contraseña*", font=("Arial", 10, "bold"), bg=COLOR_BG_GRAY, fg=COLOR_TEXT_MUTED).pack(pady=(10, 0))
entry_pass = tk.Entry(ventana, show="*", justify="center", bg=COLOR_PANEL, fg=COLOR_TEXT_MAIN, relief="solid", bd=1, font=("Arial", 11), width=22)
entry_pass.pack(pady=4, ipady=4)

btn_login = tk.Button(ventana, text="ENTRAR", command=validar_acceso, bg=COLOR_NAVY_MAIN, fg="white", 
          activebackground=COLOR_NAVY_LIGHT, activeforeground="white", 
          relief="flat", font=("Arial", 11, "bold"), width=16)
btn_login.pack(pady=(20, 5), ipady=2)
añadir_efecto_hover(btn_login, COLOR_NAVY_LIGHT, COLOR_NAVY_MAIN)

btn_olvido = tk.Button(ventana, text="¿Olvidó su contraseña?", command=abrir_ventana_recuperacion, bg=COLOR_BG_GRAY, fg=COLOR_NAVY_MAIN,
                       activebackground=COLOR_BG_GRAY, activeforeground=COLOR_NAVY_LIGHT, relief="flat", font=("Arial", 9, "underline"), cursor="hand2")
btn_olvido.pack(pady=5)

conectar_db()
ventana.mainloop()