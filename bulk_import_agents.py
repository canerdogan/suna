#!/usr/bin/env python3
"""
Toplu Agent Import Scripti
docs/prompts/ klasöründeki agent promptlarını sisteme otomatik olarak yükler
"""

import os
import json
import argparse
import requests
import random
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Default AgentPress tools - Suna config'e göre güncellendi
DEFAULT_AGENTPRESS_TOOLS = {
    'sb_shell_tool': {
        'enabled': True, 
        'description': 'Execute shell commands'
    },
    'sb_files_tool': {
        'enabled': True, 
        'description': 'Read, write, and edit files'
    },
    'sb_browser_tool': {
        'enabled': True, 
        'description': 'Browse websites and interact with web pages'
    },
    'sb_deploy_tool': {
        'enabled': True, 
        'description': 'Deploy web applications'
    },
    'sb_expose_tool': {
        'enabled': True, 
        'description': 'Expose local services to the internet'
    },
    'web_search_tool': {
        'enabled': True, 
        'description': 'Search the web for information'
    },
    'sb_vision_tool': {
        'enabled': True, 
        'description': 'Analyze and understand images'
    },
    'sb_image_edit_tool': {
        'enabled': True, 
        'description': 'Edit and manipulate images'
    },
    'sb_asset_generator_tool': {
        'enabled': True, 
        'description': 'Generate AI images, 2D game assets, and 3D game assets using Google Imagen and Eachlabs workflows'
    },
    'data_providers_tool': {
        'enabled': True, 
        'description': 'Access structured data from various providers'
    },
}

# Avatar seçenekleri
AVATARS = ['🤖', '🚀', '💡', '🎮', '⚡', '🔧', '🎨', '🧠', '💻', '🌟']
AVATAR_COLORS = ['#0984E3', '#6C5CE7', '#00B894', '#FDCB6E', '#FD79A8', '#A29BFE', '#74B9FF', '#81ECEC']

class AgentImporter:
    def __init__(self, email: str = None, password: str = None):
        # .env dosyasını yükle
        load_dotenv('backend/.env')
        
        # Supabase client oluştur
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_anon_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_anon_key:
            raise ValueError("Supabase URL ve Anon Key .env dosyasında bulunamadı")
        
        self.supabase: Client = create_client(supabase_url, supabase_anon_key)
        self.api_base_url = "http://localhost:8000"
        self.jwt_token = None
        
        # Email ve password ile giriş yap
        if email and password:
            try:
                auth_response = self.supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": password
                })
                self.jwt_token = auth_response.session.access_token
                print(f"✅ Giriş başarılı: {email}")
            except Exception as e:
                raise ValueError(f"Giriş başarısız: {e}")
        else:
            raise ValueError("Email ve password parametreleri gerekli")

    def read_markdown_file(self, file_path: Path) -> Dict[str, str]:
        """MD dosyasını okur ve YAML front matter ile agent bilgilerini çıkarır"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # YAML front matter kontrolü
            if content.startswith('---'):
                # YAML front matter'ı parse et
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    yaml_content = parts[1].strip()
                    markdown_content = parts[2].strip()
                    
                    try:
                        metadata = yaml.safe_load(yaml_content)
                        return {
                            'name': metadata.get('name', file_path.stem.replace('_', ' ').title()),
                            'description': metadata.get('description', f"Auto-imported from {file_path.name}"),
                            'system_prompt': markdown_content,
                            'groups': metadata.get('groups', []),
                            'custom_mcps': metadata.get('custom_mcps', []),
                            'agent_id': metadata.get('agent_id', ''),
                            'file_path': file_path
                        }
                    except yaml.YAMLError as e:
                        print(f"⚠️  YAML parse hatası {file_path}: {e}")
                        # YAML hatası varsa eski yöntemi kullan
                        pass
            
            # YAML front matter yoksa eski yöntemi kullan
            lines = content.split('\n')
            agent_name = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('#') and not line.startswith('##'):
                    agent_name = line.lstrip('#').strip()
                    break
            
            if not agent_name:
                agent_name = file_path.stem.replace('_', ' ').title()
            
            return {
                'name': agent_name,
                'description': f"Auto-imported from {file_path.name}",
                'system_prompt': content,
                'groups': [],
                'custom_mcps': [],
                'agent_id': '',
                'file_path': file_path
            }
            
        except Exception as e:
            print(f"❌ Dosya okuma hatası {file_path}: {e}")
            return None

    def create_agent_version(self, agent_id: str, agent_data: Dict) -> bool:
        """Mevcut agent için yeni versiyon oluşturur"""
        try:
            # Request payload hazırla
            payload = {
                'system_prompt': agent_data['system_prompt'],
                'configured_mcps': [],
                'custom_mcps': agent_data.get('custom_mcps', []),
                'agentpress_tools': DEFAULT_AGENTPRESS_TOOLS
            }
            
            # API çağrısı
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.jwt_token}'
            }
            
            response = requests.post(
                f"{self.api_base_url}/api/agent/versioning/{agent_id}",
                json=payload,
                headers=headers
            )
            
            if response.status_code in [200, 201]:
                version = response.json()
                version_name = version.get('version_name', 'unknown')
                print(f"✅ Yeni versiyon oluşturuldu: {agent_data['name']} ({version_name})")
                return True
            else:
                print(f"❌ Versiyon oluşturma hatası: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Hata detayı: {error_data}")
                except:
                    print(f"   Hata detayı: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Versiyon oluşturma hatası: {e}")
            return False

    def create_agent(self, agent_data: Dict) -> bool:
        """API üzerinden agent oluşturur"""
        try:
            # Rastgele avatar ve renk seç
            avatar = random.choice(AVATARS)
            avatar_color = random.choice(AVATAR_COLORS)
            
            # Request payload hazırla
            payload = {
                'name': agent_data['name'],
                'description': agent_data['description'],
                'system_prompt': agent_data['system_prompt'],
                'avatar': avatar,
                'avatar_color': avatar_color,
                'configured_mcps': [],
                'custom_mcps': agent_data.get('custom_mcps', []),
                'agentpress_tools': DEFAULT_AGENTPRESS_TOOLS,
                'is_default': False
            }
            
            # API çağrısı
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.jwt_token}'
            }
            
            response = requests.post(
                f"{self.api_base_url}/api/agents",
                json=payload,
                headers=headers
            )
            
            if response.status_code in [200, 201]:
                agent = response.json()
                agent_id = agent.get('agent_id', 'unknown')
                print(f"✅ Agent başarıyla oluşturuldu: {agent_data['name']} (ID: {agent_id})")
                
                # Agent ID'yi dosyaya yaz
                if 'file_path' in agent_data and agent_id != 'unknown':
                    self.update_agent_id_in_file(agent_data['file_path'], agent_id)
                
                return True
            else:
                print(f"❌ Agent oluşturma hatası: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Hata detayı: {error_data}")
                except:
                    print(f"   Hata detayı: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Agent oluşturma hatası: {e}")
            return False

    def update_agent_id_in_file(self, file_path: Path, agent_id: str):
        """YAML front matter'da agent_id'yi günceller"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    yaml_content = parts[1].strip()
                    markdown_content = parts[2].strip()
                    
                    # YAML'ı parse et ve agent_id'yi güncelle
                    metadata = yaml.safe_load(yaml_content)
                    metadata['agent_id'] = agent_id
                    
                    # Dosyayı yeniden yaz
                    new_content = f"---\n{yaml.dump(metadata, default_flow_style=False, allow_unicode=True)}---\n{markdown_content}"
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                    print(f"📝 Agent ID güncellendi: {file_path.name}")
                    
        except Exception as e:
            print(f"⚠️  Agent ID güncelleme hatası {file_path}: {e}")

    def get_existing_agents(self) -> List[str]:
        """Mevcut agent isimlerini getirir"""
        try:
            headers = {
                'Authorization': f'Bearer {self.jwt_token}'
            }
            
            response = requests.get(
                f"{self.api_base_url}/api/agents",
                headers=headers
            )
            
            if response.status_code == 200:
                agents = response.json()
                return [agent['name'] for agent in agents]
            
            return []
            
        except Exception as e:
            print(f"❌ Mevcut agent'ları getirme hatası: {e}")
            return []

    def import_agents(self, prompts_dir: str, skip_existing: bool = True) -> Dict[str, int]:
        """Toplu agent import işlemi"""
        prompts_path = Path(prompts_dir)
        
        if not prompts_path.exists():
            print(f"❌ Klasör bulunamadı: {prompts_dir}")
            return {'success': 0, 'failed': 0, 'skipped': 0}
        
        # Mevcut agent'ları getir
        existing_agents = set()
        if skip_existing:
            existing_agents = set(self.get_existing_agents())
            print(f"📋 Mevcut agent sayısı: {len(existing_agents)}")
        
        # MD dosyalarını bul
        md_files = list(prompts_path.glob('*.md'))
        
        if not md_files:
            print(f"❌ MD dosyası bulunamadı: {prompts_dir}")
            return {'success': 0, 'failed': 0, 'skipped': 0}
        
        print(f"📁 Bulunun MD dosyası sayısı: {len(md_files)}")
        
        results = {'success': 0, 'failed': 0, 'skipped': 0}
        
        for md_file in md_files:
            print(f"\n🔄 İşleniyor: {md_file.name}")
            
            # Dosyayı oku
            agent_data = self.read_markdown_file(md_file)
            if not agent_data:
                results['failed'] += 1
                continue
            
            # Mevcut agent kontrolü
            if skip_existing and agent_data['name'] in existing_agents:
                print(f"⏭️  Atlandı (zaten var): {agent_data['name']}")
                results['skipped'] += 1
                continue
            
            # Agent_id kontrolü
            existing_agent_id = agent_data.get('agent_id', '').strip()
            
            if existing_agent_id and skip_existing:
                print(f"⏭️  Atlandı (agent_id var): {agent_data['name']} (ID: {existing_agent_id})")
                results['skipped'] += 1
                continue
            elif existing_agent_id and not skip_existing:
                print(f"🔄 Mevcut agent için yeni versiyon oluşturuluyor: {agent_data['name']}")
                # Yeni versiyon oluştur
                if self.create_agent_version(existing_agent_id, agent_data):
                    results['success'] += 1
                else:
                    results['failed'] += 1
                continue
            
            # Agent oluştur
            if self.create_agent(agent_data):
                results['success'] += 1
            else:
                results['failed'] += 1
        
        return results

def main():
    parser = argparse.ArgumentParser(description='Toplu Agent Import Scripti')
    parser.add_argument('--prompts-dir', 
                       default='docs/prompts',
                       help='Prompt dosyalarının bulunduğu klasör')
    parser.add_argument('--email', 
                       required=True,
                       help='Supabase hesap email adresi')
    parser.add_argument('--password', 
                       required=True,
                       help='Supabase hesap şifresi')
    parser.add_argument('--force', 
                       action='store_true',
                       help='Mevcut agent\'ları atlamak yerine üzerine yaz')
    parser.add_argument('--api-url',
                       default='http://localhost:8000',
                       help='Backend API URL (default: http://localhost:8000)')
    
    args = parser.parse_args()
    
    try:
        # Import işlemini başlat
        importer = AgentImporter(args.email, args.password)
        importer.api_base_url = args.api_url
        
        print(f"🚀 Toplu agent import başlatılıyor...")
        print(f"   Klasör: {args.prompts_dir}")
        print(f"   API URL: {args.api_url}")
        print(f"   Mevcut agent'ları atla: {not args.force}")
        
        results = importer.import_agents(
            args.prompts_dir, 
            skip_existing=not args.force
        )
        
        print(f"\n📊 İşlem Sonuçları:")
        print(f"   ✅ Başarılı: {results['success']}")
        print(f"   ❌ Başarısız: {results['failed']}")
        print(f"   ⏭️  Atlandı: {results['skipped']}")
        print(f"   📋 Toplam: {sum(results.values())}")
        
    except Exception as e:
        print(f"❌ Script hatası: {e}")
        return 1

if __name__ == "__main__":
    main()