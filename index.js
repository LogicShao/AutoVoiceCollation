const {app, BrowserWindow, net} = require('electron');
const path = require('path');
const {spawn} = require('child_process'); // 用于启动子进程

let mainWindow;
let loadingWindow; // 用于引用加载窗口
let pythonProcess;

// --- 创建加载动画窗口 ---
const createLoadingWindow = () => {
    loadingWindow = new BrowserWindow({
        width: 400,
        height: 300,
        frame: false,
        transparent: false,
        alwaysOnTop: true,
        resizable: false,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
        },
    });
    // 加载位于 assets 目录下的 HTML 文件
    loadingWindow.loadFile(path.join(__dirname, 'assets', 'loading.html'));
};

// --- 后端 Gradio 服务管理 ---
const startPythonBackend = () => {
    // 确保使用虚拟环境中的 Python 解释器
    // 在 Windows 上: .venv\Scripts\python.exe
    // 在 Linux/Mac 上: .venv/bin/python
    const pythonExecutable = path.join(__dirname, '.venv', process.platform === 'win32' ? 'Scripts' : 'bin', process.platform === 'win32' ? 'python.exe' : 'python');

    console.log('Starting Python backend with:', pythonExecutable);

    // 启动 webui.py 脚本
    // 强制 Python 使用 UTF-8 输出，这是解决乱码问题的核心
    const spawnOptions = {
        // 将 Node.js 的环境变量与我们强制设置的编码环境变量合并
        env: {
            ...process.env,
            PYTHONIOENCODING: 'utf-8', // 强制 stdout/stderr 使用 utf-8
            PYTHONUTF8: '1',           // Python 3.7+ 强制进入 UTF-8 模式
        },
        // 不通过 shell 启动，避免额外的转义/编码问题
        shell: false
    };

    pythonProcess = spawn(pythonExecutable, ['webui.py', '--from-electron'], spawnOptions);

    // 打印后端的输出 (用于调试)，并显式用 utf8 解码
    // 由于我们强制Python使用UTF-8, 所以这里可以直接解码为UTF-8
    pythonProcess.stdout.on('data', (data) => {
        const text = data.toString('utf8');
        console.log(`Python stdout: ${text.trim()}`);
    });
    pythonProcess.stderr.on('data', (data) => {
        const text = data.toString('utf8');
        console.error(`Python stderr: ${text.trim()}`);
    });

    pythonProcess.on('close', (code) => {
        console.log(`Python process exited with code ${code}`);
    });
};

const stopPythonBackend = () => {
    if (pythonProcess) {
        console.log('Stopping Python backend...');
        pythonProcess.kill(); // 终止子进程
        pythonProcess = null;
    }
};

// --- Electron 主窗口创建 ---
const createWindow = () => {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        show: false, // 默认不显示，等待后端准备好
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
        },
        icon: path.join(__dirname, 'assets', 'icon.svg')
    });

    const gradioUrl = 'http://127.0.0.1:7860';

    const checkGradioReady = () => {
        const request = net.request(gradioUrl);
        request.on('response', (response) => {
            if (response.statusCode === 200) {
                console.log('Gradio backend is ready! Loading URL...');
                if (loadingWindow) {
                    loadingWindow.close(); // 关闭加载窗口
                    loadingWindow = null;
                }
                mainWindow.loadURL(gradioUrl);
                mainWindow.show(); // 显示主窗口
            } else {
                setTimeout(checkGradioReady, 1000);
            }
        });

        request.on('error', () => {
            console.log('Gradio not ready yet, retrying in 1 second...');
            setTimeout(checkGradioReady, 1000);
        });

        request.end();
    };

    checkGradioReady();
};

// --- Electron App 生命周期 ---

app.whenReady().then(() => {
    createLoadingWindow();
    startPythonBackend();
    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0 && !mainWindow) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('will-quit', () => {
    stopPythonBackend();
});