import os
import sys
import zipfile
import pyzipper
from pathlib import Path
import argparse

def zip_directory(source_dir: str, archive_path: str, password: str) -> None:
    """
    Создает защищенный паролем ZIP архив с AES-256 шифрованием
    """
    # Проверяем существование исходной директории
    if not os.path.exists(source_dir):
        raise FileNotFoundError(f"Source directory not found: {source_dir}")
    
    # Создаем архив с AES-256 шифрованием
    with pyzipper.AESZipFile(
        archive_path, 
        'w', 
        compression=pyzipper.ZIP_DEFLATED,
        encryption=pyzipper.WZ_AES
    ) as zf:
        # Устанавливаем пароль
        zf.setpassword(password.encode('utf-8'))
        
        source_path = Path(source_dir)
        
        # Обходим все файлы и директории
        for root, dirs, files in os.walk(source_path):
            root_path = Path(root)
            
            # Добавляем файлы
            for file in files:
                file_path = root_path / file
                # Вычисляем относительный путь для сохранения в архиве
                arcname = str(file_path.relative_to(source_path))
                zf.write(file_path, arcname)
            
            # Добавляем директории (даже пустые)
            for dir_name in dirs:
                dir_path = root_path / dir_name
                arcname = str(dir_path.relative_to(source_path)) + '/'
                zf.write(dir_path, arcname)


def unzip_archive(archive_path: str, output_dir: str, password: str) -> None:
    """
    Распаковывает защищенный паролем ZIP архив    
    Поддерживает как обычные ZIP, так и ZIP с AES шифрованием
    """
    # Проверяем существование архива
    if not os.path.exists(archive_path):
        raise FileNotFoundError(f"Archive not found: {archive_path}")
    
    # Создаем выходную директорию
    os.makedirs(output_dir, exist_ok=True)
    
    # Пытаемся открыть как AES зашифрованный архив
    try:
        with pyzipper.AESZipFile(archive_path, 'r') as zf:
            zf.setpassword(password.encode('utf-8'))
            zf.extractall(output_dir)
            return
    except (RuntimeError, pyzipper.BadZipFile):
        pass  # Возможно это обычный ZIP архив
    
    # Пробуем как обычный ZIP архив
    try:
        with zipfile.ZipFile(archive_path, 'r') as zf:
            # Проверяем, нужен ли пароль
            zf.setpassword(password.encode('utf-8'))
            
            # Проверяем первый файл для обнаружения ошибки пароля
            try:
                first_file = zf.namelist()[0]
                zf.read(first_file)
            except (RuntimeError, zipfile.BadZipFile) as e:
                if "Bad password" in str(e) or "Bad CRC-32" in str(e):
                    raise ValueError("Incorrect password")
                raise
            
            # Распаковываем все файлы
            zf.extractall(output_dir)
            
    except zipfile.BadZipFile:
        raise ValueError("File is not a valid ZIP archive")
    except RuntimeError as e:
        if "Bad password" in str(e):
            raise ValueError("Incorrect password")
        raise


def main():
    """
    Главная функция для обработки аргументов командной строки
    Аналог Rust функции main()
    """
    # Настраиваем парсер аргументов
    parser = argparse.ArgumentParser(
        description="ZIP архиватор с поддержкой AES-256 шифрования"
    )
    parser.add_argument(
        "command",
        choices=['zip', 'unzip'],
        help="Команда: zip (создать архив) или unzip (распаковать)"
    )
    parser.add_argument(
        "input",
        help="Входной путь: директория для zip или архив для unzip"
    )
    parser.add_argument(
        "output",
        help="Выходной путь: файл архива для zip или директория для unzip"
    )
    
    args = parser.parse_args()
    
    password = "12345"
    
    try:
        if args.command == "zip":
            print(f"Creating archive: {args.output} from {args.input}")
            zip_directory(args.input, args.output, password)
            print(f"Successfully created archive: {args.output}")
            
        elif args.command == "unzip":
            print(f"Extracting archive: {args.input} to {args.output}")
            unzip_archive(args.input, args.output, password)
            print(f"Successfully extracted to: {args.output}")
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()