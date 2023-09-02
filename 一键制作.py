import os
import subprocess
import time
import zipfile
from shutil import rmtree, copy
import requests
from colorama import Fore
from tqdm import tqdm
import contextpatch
import fspatch
import imgextractor
import rimg2sdat
import utils

lj = os.getcwd()
import sys


class zip_file(object):
    def __init__(self, file, dst_dir):
        os.chdir(dst_dir)
        with zipfile.ZipFile(relpath := lj + os.sep + file, 'w', compression=zipfile.ZIP_DEFLATED,
                             allowZip64=True) as zip_:
            # 遍历写入文件
            for file in get_all_file_paths('.'):
                print(f"正在写入:%s" % file)
                try:
                    zip_.write(file)
                except Exception as e:
                    print(e)
        if os.path.exists(relpath):
            print("打包成功:{}".format(relpath))
        os.chdir(lj)


def get_all_file_paths(directory) -> Ellipsis:
    # 初始化文件路径列表
    file_paths = []
    for root, directories, files in os.walk(directory):
        for filename in files:
            # 连接字符串形成完整的路径
            file_paths.append(os.path.join(root, filename))

    # 返回所有文件路径
    return file_paths


def call(exe, kz='Y', out=0, shstate=False, sp=0):
    if kz == "Y":
        cmd = f'{lj}{os.sep}bin{os.sep}{exe}'
    else:
        cmd = exe
    if os.name != 'posix':
        conf = subprocess.CREATE_NO_WINDOW
    else:
        if sp == 0:
            cmd = cmd.split()
        conf = 0
    try:
        ret = subprocess.Popen(cmd, shell=shstate, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, creationflags=conf)
        for i in iter(ret.stdout.readline, b""):
            if out == 0:
                print(i.decode("utf-8", "ignore").strip())
    except subprocess.CalledProcessError as e:
        for i in iter(e.stdout.readline, b""):
            if out == 0:
                print(e.decode("utf-8", "ignore").strip())
    ret.wait()
    return ret.returncode


def mke2fs(name, work, size):
    print(f"[{time.strftime('%H:%M:%S', time.localtime(time.time()))}]正在打包 {name}")
    fspatch.main(work + name, f'{work}config{os.sep}{name}_fs_config')
    contextpatch.main(work + name, f"{work}config{os.sep}{name}_file_contexts")
    utils.qc(f"{work}config{os.sep}{name}_fs_config")
    utils.qc(f"{work}config{os.sep}{name}_file_contexts")
    if call(
            f"mke2fs -O ^has_journal -L {name} -I 256 -M /{name} -m 0 -t ext4 -b 4096 {work + name}_new.img {size}") != 0:
        os.remove(f'{work + name}_new.img')
        print(f"创建镜像失败 {name}")
        return False
    if call(
            f"e2fsdroid -e -T {int(time.time())} -S {work}config{os.sep}{name}_file_contexts -C {work}config{os.sep}{name}_fs_config -a /{name} -f {work + name} {work + name}_new.img") != 0:
        os.remove(f'{work + name}_new.img')
        print("写入镜像失败 %s" % name)
        return False
    os.rename(work + name + "_new.img", work + name + ".img")


def datbr(name):
    tqdm.write('[' + time.strftime('%H:%M:%S', time.localtime(time.time())) + ']' + f'开始转换{name}镜像...')
    rimg2sdat.process(lj + os.sep + "ROM" + os.sep + f"{name}.img", f"-o {lj + os.sep + 'ROM'} -v 4 -p {name}")
    os.remove(lj + os.sep + "ROM" + os.sep + f"{name}.img")
    call(
        f'brotli -q 0 {lj + os.sep + "ROM" + os.sep + f"{name}.new.dat"} -o {lj + os.sep + "ROM" + os.sep + f"{name}.new.dat.br"}')
    os.remove(lj + os.sep + "ROM" + os.sep + f"{name}.new.dat")
    tqdm.write('[' + time.strftime('%H:%M:%S', time.localtime(time.time())) + ']' + f'转换{name}镜像完毕...')


def download(url, path):
    start_time = time.time()
    requests.packages.urllib3.disable_warnings()
    try:
        response = requests.Session().head(url)
        file_size = int(response.headers.get("Content-Length", 0))
        response = requests.Session().get(url, stream=True, verify=False)
        with open(path + os.sep + os.path.basename(url).split("?")[0], "wb") as f:
            chunk_size = 2048576
            bytes_downloaded = 0
            for data in response.iter_content(chunk_size=chunk_size):
                f.write(data)
                bytes_downloaded += len(data)
                elapsed = time.time() - start_time
                speed = bytes_downloaded / (1024 * elapsed)
                percentage = int(bytes_downloaded * 100 / file_size)
                print(f"进度：{percentage} % 速度:{speed} B/S 已下载：{bytes_downloaded} / {file_size} B")
    except ConnectionRefusedError and ConnectionAbortedError and requests.exceptions.ConnectionError:
        raise ChildProcessError("下载失败")


def redir(path):
    if os.path.exists(path):
        rmtree(path)
        os.makedirs(path)
    else:
        os.makedirs(path)


bb = '20230814'
zuozhe = '米欧科技'
print('[' + time.strftime('%H:%M:%S', time.localtime(time.time())) + ']' + '正在清理工作目录')
redir(lj + os.sep + "ROM")
redir(lj + os.sep + "tmp")
redir(lj + os.sep + "down")
print(Fore.GREEN + '=====米欧官改工具=====')
print('工具作者:' + zuozhe)
print('工具版本' + bb)
print(f'路径:{lj}')
try:
    romdz = sys.argv[1]
except:
    romdz = input('[' + time.strftime('%H:%M:%S', time.localtime(time.time())) + ']' + '输入ROM路径或下载地址：')
if not romdz:
    input('地址不存在')
    exit(1)
romsrc = os.path.basename(romdz).split("?")[0]
romname = time.strftime('%H_%M_%S_MIO_', time.localtime(time.time())) + romsrc
print(romname)
tqdm.write('[' + time.strftime('%H:%M:%S', time.localtime(time.time())) + ']' + f'正在下载{romsrc}...')
if os.path.exists(os.path.abspath(romdz)):
    copy(os.path.abspath(romdz), lj + os.sep + "down" + os.sep + romsrc)
else:
    Error = True
    times = 0
    while Error:
        try:
            download(romdz, lj + os.sep + "down")
        except ChildProcessError as e:
            times += 1
            print(e, f"\n第{times}次重试！")
            Error = True
        else:
            Error = False
tqdm.write('[' + time.strftime('%H:%M:%S', time.localtime(time.time())) + ']' + '开始解包ROM...')
zipfile.ZipFile(lj + os.sep + "down" + os.sep + romsrc).extractall(lj + os.sep + "ROM" + os.sep)
tqdm.write('[' + time.strftime('%H:%M:%S', time.localtime(time.time())) + ']' + '开始转换镜像...')
rmtree(lj + os.sep + "ROM" + os.sep + "META-INF")
tqdm.write('[' + time.strftime('%H:%M:%S', time.localtime(time.time())) + ']' + '开始转换SYSTEM镜像...')
call(
    f"brotli -dj {lj + os.sep + 'ROM' + os.sep + 'system.new.dat.br'} -o {lj + os.sep + 'ROM' + os.sep + 'system.new.dat'}")
utils.sdat2img(lj + os.sep + "ROM" + os.sep + "system.transfer.list", lj + os.sep + "ROM" + os.sep + "system.new.dat",
               lj + os.sep + "ROM" + os.sep + "system.img")
tqdm.write('[' + time.strftime('%H:%M:%S', time.localtime(time.time())) + ']' + '开始转换VENDOR镜像...')
call(
    f"brotli -dj {lj + os.sep + 'ROM' + os.sep + 'vendor.new.dat.br'} -o {lj + os.sep + 'ROM' + os.sep + 'vendor.new.dat'}")
utils.sdat2img(lj + os.sep + "ROM" + os.sep + "vendor.transfer.list", lj + os.sep + "ROM" + os.sep + "vendor.new.dat",
               lj + os.sep + "ROM" + os.sep + "vendor.img")
tqdm.write('[' + time.strftime('%H:%M:%S', time.localtime(time.time())) + ']' + '正在删除无用文件...')
for file in os.listdir(lj + os.sep + "ROM" + os.sep):
    if file.endswith(".br") or file.endswith(".dat") or file.endswith(".list"):
        os.remove(lj + os.sep + "ROM" + os.sep + file)
tqdm.write('[' + time.strftime('%H:%M:%S', time.localtime(time.time())) + ']' + '开始解包镜像...')
imgextractor.Extractor().main(lj + os.sep + "ROM" + os.sep + "system.img", lj + os.sep + "ROM" + os.sep + "system",
                              lj + os.sep + "ROM" + os.sep)
os.remove(lj + os.sep + "ROM" + os.sep + "system.img")
imgextractor.Extractor().main(lj + os.sep + "ROM" + os.sep + "vendor.img", lj + os.sep + "ROM" + os.sep + "vendor",
                              lj + os.sep + "ROM" + os.sep)
os.remove(lj + os.sep + "ROM" + os.sep + "vendor.img")
tqdm.write('[' + time.strftime('%H:%M:%S', time.localtime(time.time())) + ']' + '正在自动修改ROM...')
for o in [f'{os.sep}ROM{os.sep}system{os.sep}system{os.sep}recovery-from-boot.p',
          f'{os.sep}ROM{os.sep}system{os.sep}system{os.sep}app{os.sep}msa',
          f'{os.sep}ROM{os.sep}system{os.sep}system{os.sep}data-app',
          f'{os.sep}ROM{os.sep}vendor{os.sep}data-app']:
    if os.path.exists(lj + o):
        if os.path.isdir(lj + o):
            rmtree(lj + o)
        else:
            os.remove(lj + o)
copy(lj + os.sep + "bin" + os.sep + "camera_config.xml",
     lj + f'{os.sep}ROM{os.sep}vendor{os.sep}etc{os.sep}camera{os.sep}camera_config.xml')
tqdm.write('[' + time.strftime('%H:%M:%S', time.localtime(time.time())) + ']' + '开始打包镜像...')
tqdm.write(Fore.YELLOW + '[' + time.strftime('%H:%M:%S', time.localtime(
    time.time())) + ']' + '程序暂停，你可以手动修改ROM,或者任意按键继续...')
input()
mke2fs("system", "".join([lj, os.sep, "ROM", os.sep]), "4096M")
mke2fs("vendor", "".join([lj, os.sep, "ROM", os.sep]), "1024M")
tqdm.write('[' + time.strftime('%H:%M:%S', time.localtime(time.time())) + ']' + '开始转换镜像')
datbr("system")
datbr("vendor")
tqdm.write('[' + time.strftime('%H:%M:%S', time.localtime(time.time())) + ']' + '写入刷机脚本...')
zipfile.ZipFile(lj + os.sep + "bin" + os.sep + "TY.zip").extractall(lj + os.sep + "ROM" + os.sep)
tqdm.write('[' + time.strftime('%H:%M:%S', time.localtime(time.time())) + ']' + '正在删除临时文件...')
for s in os.listdir(lj + os.sep + "ROM"):
    if os.path.isdir(lj + os.sep + "ROM" + s):
        if s in ["system", "vendor", "firmware-update"]:
            rmtree(lj + os.sep + "ROM" + s)
tqdm.write('[' + time.strftime('%H:%M:%S', time.localtime(time.time())) + ']' + '开始打包ROM...')
zip_file(romname + '.zip', lj + os.sep + "ROM")
tqdm.write('[' + time.strftime('%H:%M:%S',
                               time.localtime(time.time())) + ']' + '完成，ROM输出到' + lj + '\\' + romname + '.zip')
tqdm.write('[' + time.strftime('%H:%M:%S', time.localtime(time.time())) + ']' + '感谢您使用与信任米欧工具。')
tqdm.write('[' + time.strftime('%H:%M:%S', time.localtime(time.time())) + ']' + '任意按钮退出。')
input("任意按钮退出")
