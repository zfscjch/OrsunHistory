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
            const isRight = answer === titles[num].answer;
            sendMessage(username, "POST", {num: num, isRight: isRight}, (data) => {
                console.log(data);
                if (data.status === 'success' && isRight) {
                    handleVerifySuccess();
                } else if (data.status === 'success' && !isRight) {
                    window.location.href = "/not_allow?code=401";
                } else {
                    showMessage(data.msg, "error");
                }
            });
        });

        sendMessage(username, "GET",null, (data) => {
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
            window.location.href = "/not_allow?code=403";
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
function sendMessage(username, request="GET", d=null, handler = (r) => {console.log(r)}) {
    const data = {
        name: username,
        request: request,
        msg: d
    };

    if (!d) delete data.msg;

    fetch("/api/titles", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
    })
        .then((res) => {
            if (!res.ok) {
                throw new Error(`HTTP error! status: ${res.status}`);
            }
            return res.json();
        })
        .then(data => {
            console.log("服务器响应:", data);

            if (data.status === "error") {
                showMessage(data.message || "服务器错误", 'error');
                return;
            }

            handler(data);
        })
        .catch((err) => {
            console.error("请求错误:", err);
            showMessage("网络错误或服务器无响应", 'error');
        });
}

// 处理登录成功
function handleVerifySuccess() {
    showMessage('验证成功，正在跳转...', 'success');
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
    }, 1);
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

const urlSearchParams = new URLSearchParams(window.location.search);
const username = sessionStorage.getItem("user");
const isTeacher = sessionStorage.getItem("isTeacher");

if (!username) {
    window.location.href = "/login";
}

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
    await initApp();
});

