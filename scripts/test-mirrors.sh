#!/bin/bash
# ================================
# 测试各个镜像源的连接速度
# ================================

echo "Testing Ubuntu mirror sources..."
echo "================================"
echo ""

# 定义镜像源列表
declare -A mirrors=(
    ["清华大学"]="mirrors.tuna.tsinghua.edu.cn"
    ["阿里云"]="mirrors.aliyun.com"
    ["中科大"]="mirrors.ustc.edu.cn"
    ["网易"]="mirrors.163.com"
    ["华为云"]="mirrors.huaweicloud.com"
    ["腾讯云"]="mirrors.cloud.tencent.com"
)

# 测试函数
test_mirror() {
    local name=$1
    local url=$2
    local test_url="http://${url}/ubuntu/dists/jammy/InRelease"

    echo -n "Testing ${name} (${url})... "

    # 使用 curl 测试连接，设置 5 秒超时
    if curl -s -m 5 -o /dev/null -w "%{http_code}" "${test_url}" | grep -q "200"; then
        # 测试下载速度
        local speed=$(curl -s -w "%{speed_download}" -o /dev/null -m 5 "${test_url}")
        echo "✓ OK (Speed: ${speed} bytes/s)"
        return 0
    else
        echo "✗ Failed"
        return 1
    fi
}

# 测试所有镜像源
fastest_mirror=""
fastest_name=""

for name in "${!mirrors[@]}"; do
    url="${mirrors[$name]}"
    if test_mirror "$name" "$url"; then
        if [ -z "$fastest_mirror" ]; then
            fastest_mirror="$url"
            fastest_name="$name"
        fi
    fi
done

echo ""
echo "================================"
if [ -n "$fastest_mirror" ]; then
    echo "Fastest mirror: ${fastest_name} (${fastest_mirror})"
    echo ""
    echo "To use this mirror, update Dockerfile line 21-22:"
    echo ""
    echo "RUN sed -i 's@//.*archive.ubuntu.com@//${fastest_mirror}@g' /etc/apt/sources.list && \\"
    echo "    sed -i 's@//.*security.ubuntu.com@//${fastest_mirror}@g' /etc/apt/sources.list"
    echo ""
else
    echo "No mirror is accessible. You may need to:"
    echo "1. Check your network connection"
    echo "2. Use a proxy"
    echo "3. Try again later"
fi
