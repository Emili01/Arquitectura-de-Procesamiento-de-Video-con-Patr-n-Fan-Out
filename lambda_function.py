import boto3
import subprocess
import json
import os
import urllib.request
import tarfile
import shutil
from decimal import Decimal
from botocore.config import Config
import time
import random

print("--- LAMBDA INICIADA V13 - DYNAMODB DECIMAL FIX ---")

LOCALSTACK_HOST = os.environ.get('LOCALSTACK_HOSTNAME', 'localhost')
ENDPOINT_URL = f"http://{LOCALSTACK_HOST}:4566"
TARGET_RESOLUTION = os.environ.get('TARGET_RESOLUTION', '720p') 

RESOLUTIONS = {
    '720p': '1280:720',
    '480p': '852:480'
}

print(f"--- LAMBDA INICIADA: {TARGET_RESOLUTION} ---")

s3_config = Config(s3={'addressing_style': 'path'})
s3 = boto3.client('s3', endpoint_url=ENDPOINT_URL, config=s3_config, region_name='us-east-1', aws_access_key_id='test', aws_secret_access_key='test')
dynamodb = boto3.resource('dynamodb', endpoint_url=ENDPOINT_URL, region_name='us-east-1', aws_access_key_id='test', aws_secret_access_key='test')
table = dynamodb.Table('VideoMetadata')

FFMPEG_PATH = None

def get_ffmpeg():
    """Obtener FFmpeg: buscar o descargar automáticamente"""
    global FFMPEG_PATH
    
    if FFMPEG_PATH and os.path.isfile(FFMPEG_PATH) and os.access(FFMPEG_PATH, os.X_OK):
        return FFMPEG_PATH
    
    search_paths = [
        '/opt/bin/ffmpeg',
        '/tmp/ffmpeg/ffmpeg',
        '/usr/local/bin/ffmpeg',
        '/usr/bin/ffmpeg',
    ]
    
    print("Buscando FFmpeg...")
    for path in search_paths:
        if os.path.isfile(path):
            size_mb = os.path.getsize(path) / (1024*1024)
            print(f"   Encontrado: {path} ({size_mb:.1f} MB)")
            if os.access(path, os.X_OK):
                print(f"Ejecutable")
                FFMPEG_PATH = path
                return path
            else:
                try:
                    os.chmod(path, 0o755)
                    if os.access(path, os.X_OK):
                        print(f"   ✅ Permisos corregidos")
                        FFMPEG_PATH = path
                        return path
                except Exception as e:
                    print(f"   ❌ Error: {e}")
    
    print("FFmpeg no encontrado. Iniciando descarga automática...")
    return download_ffmpeg()

def download_ffmpeg():
    """Descargar FFmpeg estático a /tmp/"""
    global FFMPEG_PATH
    
    ffmpeg_dir = "/tmp/ffmpeg"
    ffmpeg_bin = os.path.join(ffmpeg_dir, "ffmpeg")
    
    if os.path.isfile(ffmpeg_bin) and os.access(ffmpeg_bin, os.X_OK):
        FFMPEG_PATH = ffmpeg_bin
        return ffmpeg_bin
    
    try:
        os.makedirs(ffmpeg_dir, exist_ok=True)
        
        url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
        tar_path = "/tmp/ffmpeg.tar.xz"
        
        print(f" Descargando FFmpeg...")
        
        urllib.request.urlretrieve(url, tar_path)
        
        file_size = os.path.getsize(tar_path)
        print(f"   ✅ Descarga completada: {file_size/(1024*1024):.1f} MB")
        
        print(" Extrayendo binarios...")
        with tarfile.open(tar_path, 'r:xz') as tar:
            for member in tar.getmembers():
                basename = os.path.basename(member.name)
                if basename in ['ffmpeg', 'ffprobe']:
                    member.name = basename
                    tar.extract(member, ffmpeg_dir)
                    extracted_size = os.path.getsize(os.path.join(ffmpeg_dir, basename))
                    print(f"   ✅ {basename}: {extracted_size/(1024*1024):.1f} MB")
        
        os.chmod(ffmpeg_bin, 0o755)
        ffprobe_bin = os.path.join(ffmpeg_dir, "ffprobe")
        if os.path.isfile(ffprobe_bin):
            os.chmod(ffprobe_bin, 0o755)
        
        result = subprocess.run([ffmpeg_bin, '-version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"   ✅ {version_line}")
        else:
            raise Exception("FFmpeg no responde")
        
        # Limpiar
        os.remove(tar_path)
        
        FFMPEG_PATH = ffmpeg_bin
        return ffmpeg_bin
        
    except Exception as e:
        print(f"❌ Error en la descarga: {e}")
        if os.path.exists(tar_path):
            os.remove(tar_path)
        if os.path.exists(ffmpeg_dir):
            shutil.rmtree(ffmpeg_dir)
        raise


def lambda_handler(event, context):
    ffmpeg = get_ffmpeg()
    scale_filter = RESOLUTIONS.get(TARGET_RESOLUTION, '1280:720')
    
    if 'Records' not in event:
        return {'statusCode': 200, 'body': 'Sin registros'}

    for record in event['Records']:
        local_video = None
        processed_video = None
        
        try:
            sqs_body = json.loads(record['body'])
            body = json.loads(sqs_body['Message']) if 'Message' in sqs_body else sqs_body
            
            if 'Records' not in body:
                print(f"Evento ignorado (TestEvent)")
                continue

            s3_event = body['Records'][0]
            bucket = s3_event['s3']['bucket']['name']
            key = s3_event['s3']['object']['key']
            
            print(f"🎬 Procesando: {key} a {TARGET_RESOLUTION}")
            
            unique_id = context.aws_request_id
            local_video = f"/tmp/{unique_id}_{TARGET_RESOLUTION}_{os.path.basename(key)}"
            processed_video = f"/tmp/processed_{unique_id}_{TARGET_RESOLUTION}_{os.path.basename(key)}"
            
            if TARGET_RESOLUTION == '480p':
                time.sleep(random.randint(1, 3)) 
            
            s3.download_file(bucket, key, local_video)            
            
            if not os.path.exists(local_video) or os.path.getsize(local_video) == 0:
                raise Exception(f"El archivo descargado está vacío o no existe: {local_video}")
            
            input_size = os.path.getsize(local_video)

            cmd = [
                ffmpeg, '-y', '-i', local_video,
                '-vf', f"scale={scale_filter}:force_original_aspect_ratio=decrease,pad=ceil(iw/2)*2:ceil(ih/2)*2",
                '-c:a', 'copy', '-preset', 'fast', '-movflags', '+faststart',
                processed_video
            ]

            try:
                subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=True)
            except subprocess.CalledProcessError as e:
               
                print(f"❌ ERROR DE FFMPEG: {e.stderr}")
                raise e 
           
            output_size = os.path.getsize(processed_video)
            reduction = round((1 - output_size/input_size) * 100, 2)
            
            output_key = f"{TARGET_RESOLUTION}_{key}"
            s3.upload_file(processed_video, 'bucket-b-processed', output_key)
            
            table.put_item(Item={
                'video_id': key,
                'resolution': TARGET_RESOLUTION,
                'status': 'SUCCESS',
                'input_size_mb': Decimal(str(round(input_size/(1024*1024), 2))),
                'output_size_mb': Decimal(str(round(output_size/(1024*1024), 2))),
                'reduction_percent': Decimal(str(reduction)),
                'timestamp': context.aws_request_id
            })
            
            print(f"✅ Éxito: {TARGET_RESOLUTION}")
            
        except Exception as e:
            print(f"❌ Error fatal en {TARGET_RESOLUTION}: {e}")
            raise e
        finally:
            for file_path in [local_video, processed_video]:
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"🧹 Archivo temporal eliminado: {os.path.basename(file_path)}")
                    except Exception as e:
                        print(f"⚠️ No se pudo eliminar {file_path}: {e}")

    return {'statusCode': 200, 'body': 'Procesado'}
