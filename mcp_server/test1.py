import os

if __name__ == '__main__':
    import subprocess

    file_in = 'C:\\Users\\23317\\Desktop\\1\\端侧算力.pdf'

    # 这是输出的临时文件夹，文件夹名称取文件名称，里面有md文件
    file_out = 'C:\\Users\\23317\\.mineru\\temp\\端侧算力'

    print(f"Extracting with mineru: {file_in}")

    cmd = 'mineru-open-api extract %s -o %s -f md' % (file_in, file_out)
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')