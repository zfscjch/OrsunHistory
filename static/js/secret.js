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

async function autoLogin() {
    const autoLoginData = localStorage.getItem("Orsun_Auto_Login");
    const userData = localStorage.getItem("Orsun_User_Data");
    if (!autoLoginData) return false;

    const config = JSON.parse(autoLoginData);
    const data = JSON.parse(userData);
    console.log(config, data);

    // 检查配置是否有效
    if (!config.enabled || !config.username || !config.password) return false;

    // 检查是否过期（可选：设置30天有效期）
    if (config.expireTime && new Date().getTime() > config.expireTime) return false;


    const isContinue = confirm("(article.html)用户" + config.username + "开启了自动登录，请问是否继续自动登录？");
    if (!isContinue) return false;

    sessionStorage.setItem("user", config.username);
    sessionStorage.setItem("isTeacher", data.isTeacher);

    try {
        const res = await fetch("/api/get-id", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ user: config.username }),
        });
        const d = await res.json();
        sessionStorage.setItem("userID", d.id);
        return true;
    } catch (e) {
        console.error(e);
        alert("用户ID获取失败，请重新登录！");
        return false;
    }
}

const username = sessionStorage.getItem("user");
const isTeacher = sessionStorage.getItem("isTeacher");

let loop, body, app, verifyContainer, settings;
loop = null;
settings = {showVerify: null, showSayings: null};
let titles = [];
let num = -1;
const currentHash = window.location.hash;
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
        const result = await autoLogin();
        if(!result) window.location.href = "/login";
    }
    await initApp();
});
