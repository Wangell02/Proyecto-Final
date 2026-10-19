import re

with open(r"PEA-Scraper/DLDD-MAFF-JDLA.py", "r", encoding="utf-8") as f:
    content = f.read()

# Import test_csv_extractor_prototype definition to obtain the clean code of CSVExtractor
with open(r"scratch/test_csv_extractor_prototype.py", "r", encoding="utf-8") as f_proto:
    proto_code = f_proto.read()

# Extract ALIAS_MAP and CSVExtractor from proto_code
pos_alias = proto_code.find("ALIAS_MAP = {")
pos_proto_end = proto_code.find("print(\"CSVExtractor class defined successfully.\")")
csv_extractor_block = proto_code[pos_alias:pos_proto_end].strip()

# 1. Insert ALIAS_MAP and CSVExtractor right above ApplicationService
target_app_service = "# CAPA DE SERVICIOS Y LOGICA DE APLICACION\n# =========================================================================\n\nclass ApplicationService:"
assert target_app_service in content, "Target ApplicationService not found!"

insertion_text = f"""# =========================================================================
# MOTOR DE EXTRACCION DE ARCHIVOS CSV (4 CAPAS MINCIENCIAS)
# =========================================================================

{csv_extractor_block}


# =========================================================================
{target_app_service}"""

content = content.replace(f"# =========================================================================\n{target_app_service}", insertion_text, 1)

# 2. Add process_csv_file and process_csv_files to ApplicationService
old_process_pdf_end = '            return False, {}, "Tipo de entidad no reconocido en el resultado del PDF."'

new_csv_services = '''            return False, {}, "Tipo de entidad no reconocido en el resultado del PDF."

    def process_csv_file(self, file_path: str) -> Tuple[bool, Dict[str, Any], str]:
        extractor = CSVExtractor()
        ok, result, message = extractor.extract(file_path)
        if not ok:
            self._event("Error al procesar archivo CSV: " + message)
            return False, {}, message

        tipo = result.get("tipo", "")
        if tipo == "INVESTIGADOR":
            added, add_msg = self.add_scraped_result(result)
            if added:
                self._event("Investigador cargado desde CSV: " + str(result.get("nombre", "")))
                return True, result, add_msg
            else:
                return False, result, add_msg
        elif tipo == "GRUPO":
            added, add_msg = self.add_scraped_result(result)
            if added:
                self._event("Grupo cargado desde CSV: " + str(result.get("nombreGrupo", "")))
                return True, result, add_msg
            else:
                return False, result, add_msg
        elif tipo == "LOTE":
            grupos_cargados = 0
            grupos_duplicados = 0
            invs_cargados = 0
            invs_duplicados = 0

            grupos_list = result.get("grupos", [])
            g_idx = 0
            while g_idx < len(grupos_list):
                g = grupos_list[g_idx]
                add_ok, _ = self.add_scraped_result(g)
                if add_ok:
                    grupos_cargados += 1
                else:
                    grupos_duplicados += 1
                g_idx += 1

            invs_list = result.get("investigadores", [])
            i_idx = 0
            while i_idx < len(invs_list):
                inv = invs_list[i_idx]
                add_ok, _ = self.add_scraped_result(inv)
                if add_ok:
                    invs_cargados += 1
                else:
                    invs_duplicados += 1
                i_idx += 1

            summary_msg = "Lote CSV procesado: {} grupo(s) y {} investigador(es) incorporados (Duplicados omitidos: {} grupos, {} investigadores).".format(
                grupos_cargados, invs_cargados, grupos_duplicados, invs_duplicados
            )
            self._event(summary_msg)
            return True, result, summary_msg
        else:
            return False, {}, "Tipo de entidad no reconocido en el resultado del CSV."

    def process_csv_files(self, file_paths: List[str]) -> Dict[str, Any]:
        report = {
            "total_archivos": len(file_paths),
            "archivos_exitosos": 0,
            "archivos_fallidos": 0,
            "total_incorporados": 0,
            "total_duplicados": 0,
            "detalles": []
        }

        f_idx = 0
        while f_idx < len(file_paths):
            f_path = file_paths[f_idx]
            ok_f, res_f, msg_f = self.process_csv_file(f_path)
            detalle = {
                "archivo": os.path.basename(f_path),
                "ruta": f_path,
                "exito": ok_f,
                "mensaje": msg_f,
                "incorporados": 0,
                "duplicados": 0,
                "resultado": res_f
            }
            if ok_f:
                report["archivos_exitosos"] += 1
                tipo_f = res_f.get("tipo", "")
                if tipo_f == "INVESTIGADOR" or tipo_f == "GRUPO":
                    detalle["incorporados"] = 1
                    report["total_incorporados"] += 1
                elif tipo_f == "LOTE":
                    n_g = len(res_f.get("grupos", []))
                    n_i = len(res_f.get("investigadores", []))
                    detalle["incorporados"] = n_g + n_i
                    report["total_incorporados"] += n_g + n_i
            else:
                report["archivos_fallidos"] += 1
                if "ya se encuentra cargado" in msg_f.lower():
                    detalle["duplicados"] = 1
                    report["total_duplicados"] += 1

            report["detalles"].append(detalle)
            f_idx += 1

        return report'''

assert old_process_pdf_end in content, "old_process_pdf_end not found!"
content = content.replace(old_process_pdf_end, new_csv_services, 1)

# 3. Update PEARequestHandler._handle_cargar_archivo
old_handle_pdf = '''                if tipo_archivo == "pdf" or ruta.lower().endswith(".pdf"):
                    extractor = PDFExtractor()
                    ok, result, message = extractor.extract(ruta)
                    if ok:
                        payload = serialize_result(result)
                    else:
                        payload = serialize_error(message)
                    self._send(200, payload, "text/plain")
                else:
                    self._send(200, serialize_error("Tipo de archivo no soportado en esta etapa."), "text/plain")'''

new_handle_pdf_csv = '''                if tipo_archivo == "pdf" or ruta.lower().endswith(".pdf"):
                    extractor = PDFExtractor()
                    ok, result, message = extractor.extract(ruta)
                    if ok:
                        payload = serialize_result(result)
                    else:
                        payload = serialize_error(message)
                    self._send(200, payload, "text/plain")
                elif tipo_archivo == "csv" or ruta.lower().endswith(".csv"):
                    extractor_csv = CSVExtractor()
                    ok, result, message = extractor_csv.extract(ruta)
                    if ok:
                        payload = serialize_result(result)
                    else:
                        payload = serialize_error(message)
                    self._send(200, payload, "text/plain")
                else:
                    self._send(200, serialize_error("Tipo de archivo no soportado en esta etapa."), "text/plain")'''

assert old_handle_pdf in content, "old_handle_pdf not found!"
content = content.replace(old_handle_pdf, new_handle_pdf_csv, 1)

# 4. Update GUI in PEAApp
old_gui_button = 'ttk.Button(left, text="📄 Cargar archivo PDF (CvLAC / GrupLAC)", style="Primary.TButton", command=do_load_pdf).pack(fill="x", padx=18, pady=(0, 14))'

new_gui_buttons = '''        def do_load_csv() -> None:
            file_paths = filedialog.askopenfilenames(
                title="Seleccionar archivo(s) CSV de MinCiencias (CvLAC o GrupLAC)",
                filetypes=[("Archivos CSV (*.csv)", "*.csv")]
            )
            if file_paths:
                result_text.delete("1.0", "end")
                result_text.insert("end", "Procesando {} archivo(s) CSV...\n\n".format(len(file_paths)))
                self.status.set("Extrayendo información desde archivo(s) CSV...")

                def worker() -> None:
                    report = self.service.process_csv_files(list(file_paths))
                    def finish() -> None:
                        result_text.delete("1.0", "end")
                        result_text.insert("end", "=== RESUMEN DE IMPORTACIÓN CSV ===\n")
                        result_text.insert("end", "Total archivos seleccionados: {}\n".format(report.get("total_archivos", 0)))
                        result_text.insert("end", "Archivos procesados con éxito: {}\n".format(report.get("archivos_exitosos", 0)))
                        result_text.insert("end", "Archivos con errores o rechazados: {}\n".format(report.get("archivos_fallidos", 0)))
                        result_text.insert("end", "Entidades incorporadas: {}\n".format(report.get("total_incorporados", 0)))
                        result_text.insert("end", "Entidades duplicadas omitidas: {}\n\n".format(report.get("total_duplicados", 0)))

                        result_text.insert("end", "--- DETALLES POR ARCHIVO ---\n")
                        last_valid_result = None
                        detalles = report.get("detalles", [])
                        d_idx = 0
                        while d_idx < len(detalles):
                            det = detalles[d_idx]
                            estado_txt = "ÉXITO"
                            if not det.get("exito", False):
                                estado_txt = "RECHAZADO"
                            result_text.insert("end", "[{}] {}: {}\n".format(estado_txt, det.get("archivo", ""), det.get("mensaje", "")))
                            if det.get("exito", False) and det.get("resultado"):
                                last_valid_result = det.get("resultado")
                            d_idx += 1

                        if last_valid_result:
                            tipo_last = last_valid_result.get("tipo", "")
                            if tipo_last == "INVESTIGADOR":
                                render_summary("investigador", last_valid_result)
                            elif tipo_last == "GRUPO":
                                render_summary("grupo", last_valid_result)
                            elif tipo_last == "LOTE":
                                render_lote_summary(last_valid_result)

                        res_msg = "Procesados: {} exitosos, {} fallidos.".format(
                            report.get("archivos_exitosos", 0), report.get("archivos_fallidos", 0)
                        )
                        self.status.set(res_msg)
                    self.after(0, finish)
                threading.Thread(target=worker, daemon=True).start()

        ttk.Button(left, text="📄 Cargar archivo PDF (CvLAC / GrupLAC)", style="Primary.TButton", command=do_load_pdf).pack(fill="x", padx=18, pady=(0, 6))
        ttk.Button(left, text="📊 Cargar archivo(s) CSV (CvLAC / GrupLAC)", style="Primary.TButton", command=do_load_csv).pack(fill="x", padx=18, pady=(0, 14))'''

assert old_gui_button in content, "old_gui_button not found!"
content = content.replace(old_gui_button, new_gui_buttons, 1)

with open(r"PEA-Scraper/DLDD-MAFF-JDLA.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Actualización de PEA-Scraper/DLDD-MAFF-JDLA.py para CSV completada con éxito!")
