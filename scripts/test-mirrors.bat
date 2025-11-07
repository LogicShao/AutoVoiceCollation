@echo off
REM ================================
REM 测试各个镜像源的连接速度 (Windows)
REM ================================

echo Testing Ubuntu mirror sources...
echo ================================
echo.

REM 测试清华大学镜像源
echo Testing Tsinghua University...
curl -s -m 5 -o nul -w "HTTP Status: %%{http_code}" http://mirrors.tuna.tsinghua.edu.cn/ubuntu/dists/jammy/InRelease
echo.

REM 测试阿里云镜像源
echo Testing Aliyun...
curl -s -m 5 -o nul -w "HTTP Status: %%{http_code}" http://mirrors.aliyun.com/ubuntu/dists/jammy/InRelease
echo.

REM 测试中科大镜像源
echo Testing USTC...
curl -s -m 5 -o nul -w "HTTP Status: %%{http_code}" http://mirrors.ustc.edu.cn/ubuntu/dists/jammy/InRelease
echo.

REM 测试网易镜像源
echo Testing 163...
curl -s -m 5 -o nul -w "HTTP Status: %%{http_code}" http://mirrors.163.com/ubuntu/dists/jammy/InRelease
echo.

REM 测试华为云镜像源
echo Testing Huawei Cloud...
curl -s -m 5 -o nul -w "HTTP Status: %%{http_code}" http://mirrors.huaweicloud.com/ubuntu/dists/jammy/InRelease
echo.

echo ================================
echo.
echo If HTTP Status is 200, that mirror is working.
echo Update Dockerfile to use the fastest mirror.
echo.
pause
