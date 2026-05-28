# Claude Skill Sandbox 镜像
# 用于模式二/三在隔离容器里动态执行 skill 脚本。
#
# 构建：
#   docker build -t claude-skill-sandbox code/
#
# 镜像内含：python3 + bash + strace + tcpdump + Node.js 18 + Claude Code CLI。
# 蜜罐假凭证、runner 脚本均由宿主机在运行时挂载/写入，不烤进镜像。
#
# 运行时（由 asg/vm_ssh.py 自动调用，无需手动）：
#   docker run --rm \
#     --cap-add=SYS_ADMIN --cap-add=NET_ADMIN --cap-add=SYS_PTRACE \
#     --security-opt seccomp=unconfined --security-opt apparmor=unconfined \
#     -v <skill>:/skill:ro -v <logs>:/logs:rw -v <fake_home>:/home/codexsafe:rw \
#     -e HOME=/home/codexsafe ... claude-skill-sandbox bash /skill/_asg_paper_runner.sh ...

FROM python:3.10-slim

# （可选）国内构建时换源加速；在国外网络可删掉这一段。
RUN rm -f /etc/apt/sources.list.d/debian.sources && \
    printf 'Types: deb\nURIs: https://mirrors.ustc.edu.cn/debian\nSuites: bookworm bookworm-updates\nComponents: main contrib non-free non-free-firmware\n\nTypes: deb\nURIs: https://mirrors.ustc.edu.cn/debian-security\nSuites: bookworm-security\nComponents: main contrib non-free non-free-firmware\n' \
    > /etc/apt/sources.list.d/debian.sources || true

# 系统依赖：strace/tcpdump 是动态证据采集的核心
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        strace \
        tcpdump \
        curl \
        wget \
        git \
        sudo \
        file \
        procps \
        iputils-ping \
        net-tools \
        jq \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Node.js 18（Claude Code CLI 需要）—— 仅模式三用到，模式二可忽略
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Claude Code CLI（模式三：容器内让 Claude 使用 skill）
RUN npm install -g @anthropic-ai/claude-code || \
    echo "warn: claude-code 安装失败（仅影响模式三，模式二不受影响）"

WORKDIR /app

# 非 root 用户（uid 1000，与宿主机挂载的假 HOME 属主对齐）
RUN useradd -m -u 1000 -s /bin/bash appuser && \
    mkdir -p /app/logs && \
    chown -R appuser:appuser /app

ENV PYTHONUNBUFFERED=1

USER appuser
CMD ["/bin/bash"]
