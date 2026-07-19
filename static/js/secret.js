async function initApp() {
    settings = await getSettings();
    if (!settings.showVerify) {
        handleVerifySuccess();
        return;
    }

    try {
        // 等待fetch完成
        const response = await fetch("/avoid_titles");
        verifyContainer.innerHTML = await response.text();

        // 等待一下确保DOM渲染
        await new Promise(resolve => setTimeout(resolve, 100));

        // 初始化表单事件
        document.getElementById('title-form').addEventListener('submit', (e) => {
            e.preventDefault();
            const answer = document.getElementById('answer').value.trim();
            const messageElement = document.getElementById('message');

            // 重置消息提示
            messageElement.textContent = '';
            messageElement.className = 'error-message';

            // 显示登录中状态
            showMessage('验证中...', 'success');
            const rightAnswer = titles[num].answer;
            const isRight = answer === rightAnswer;
            showMessage(`回答${ isRight ? "正确" : "错误，正确答案是：" + rightAnswer }。即将跳转……`);
            setTimeout(handleVerifySuccess, 3000);
        });

        await sendMessage((data) => {
            titles = data.msg;
            if (titles.length > 0) {
                num = Math.floor(Math.random() * titles.length);
                document.querySelector("#v-title").innerHTML = titles[num].title;
                mainLoop();
            }
        });
    } catch (error) {
        console.error('初始化失败:', error);
    }
}

function mainLoop() {
    loop = setInterval(() => {
        const progress = document.getElementById('time');
        const showTimeEl = document.getElementById('time-show');
        let time = parseInt(progress.value);
        time--;
        progress.value = time.toString();
        showTimeEl.textContent = time.toString();

        if (time <= 0) {
            clearInterval(loop);
            handleVerifySuccess();
        }
    }, 1000);
}

// 显示消息
function showMessage(message, type) {
    const messageElement = document.getElementById('message');
    if (!messageElement) return;
    messageElement.textContent = message;
    messageElement.className = type === 'error' ? 'error-message' : 'success-message';
}

// 发送消息到服务器
async function sendMessage(handler = (r) => {console.log(r)}) {
    try {
        const res = await fetch('/api/titles');
        const data = await res.text();
        handler(JSON.parse(data));
    } catch (e) {
        console.error(e);
        showMessage("获取题目时发生错误：" + e, "error");
    }
}

// 处理登录成功
function handleVerifySuccess() {
    showMessage('验证结束，正在跳转...', 'success');
    if (loop) clearInterval(loop);
    setTimeout(() => {
        verifyContainer.style.display = "none";
        verifyContainer.innerHTML = "";
        styles.forEach(style => {
            style.media = "all";
        });
        app.style.display = "block";
        const currentHash = sessionStorage.getItem("articleHash");
        sessionStorage.removeItem("articleHash");
        window.location.hash = currentHash;

        // 使用 pushState 确保锚点生效
        if (currentHash) {
            history.pushState(null, null, currentHash);
            // 手动滚动到锚点元素
            const targetId = currentHash.substring(1);
            const targetElement = document.getElementById(targetId);
            if (targetElement) {
                targetElement.scrollIntoView();
            }
        }
        document.dispatchEvent(new Event("verifySuccess"));
    }, 500);
}

async function getSettings() {
    const settings = sessionStorage.getItem("settings");
    if (settings) return JSON.parse(settings);
    const userId = sessionStorage.getItem("userID");
    const res = await fetch("/api/settings", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({userID: userId})
    });
    const data = await res.json();
    console.log(data);
    return data.settings;
}

const username = sessionStorage.getItem("user");
const isTeacher = sessionStorage.getItem("isTeacher");

let loop, body, app, verifyContainer, settings;
loop = null;
settings = {showVerify: null, showSayings: null};
let titles = [];
let num = -1;
sessionStorage.setItem("articleHash", window.location.hash);
const styles = document.querySelectorAll("style, link[rel='stylesheet']");
styles.forEach(style => {
    style.media = "not-all";
});

// 启动应用
document.addEventListener('DOMContentLoaded', async () => {
    app = document.querySelector("#app");
    verifyContainer = document.querySelector("#verify-container");
    app.style.display = "none";
    verifyContainer.style.display = "block";
    if (!username) {
        window.location.href = "/login";
    }
    await initApp();
});
