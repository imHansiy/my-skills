---
name: localtunnel-auto-expose
description: 当启动新服务或者用户需要外部访问时，自动使用 npx 启动 LocalTunnel，并告诉用户访问公网地址和密码。
license: MIT
compatibility: opencode
---

# LocalTunnel 自动暴露服务

## 作用
当你启动了一个新的本地网络服务（或者运行在特定端口的开发服务器），或者用户明确要求提供外部/公网访问地址来进行演示、Webhook 测试、或者移动端测试时，使用此 Skill。

## 执行步骤

1. **确定端口**：首先确认本地服务运行的端口号（例如 3000, 5173, 8080 等）。如果无法从上下文中得出，请询问用户。
2. **启动 LocalTunnel**：
   使用以下命令启动 LocalTunnel，请务必以**后台运行**或**非阻塞方式**启动（例如使用 `run_command` 发送到后台）：
   ```bash
   npx localtunnel --port <端口号>
   ```
3. **提取公网 URL**：
   查看 LocalTunnel 的输出状态，它会打印类似 `your url is: https://<随机字符串>.loca.lt`。这就是用户的**公网访问地址**。
4. **获取访问密码**：
   LocalTunnel 默认需要一个密码（通常是运行机器的公网 IP）来绕过防钓鱼警告页面。请通过执行以下命令来获取该密码，根据当前操作系统选择对应命令：
   - **Windows (PowerShell)**:
     ```powershell
     (Invoke-RestMethod https://loca.lt/mytunnelpassword).ToString().Trim()
     ```
   - **Windows (CMD)**:
     ```cmd
     curl -s https://loca.lt/mytunnelpassword
     ```
   - **Linux / macOS (Bash / Zsh)**:
     ```bash
     curl -s https://loca.lt/mytunnelpassword
     ```
5. **告知用户**：
   获取到 URL 和密码后，使用清晰的 Markdown 格式反馈给用户。

## 反馈模板示例

```markdown
**LocalTunnel 隧道已启动** 🚀

- **本地服务**: `http://localhost:<端口号>`
- **公网地址**: `https://<获取到的随机名称>.loca.lt`
- **访问密码**: `<获取到的密码>`

> **提示**：首次在浏览器中访问公网地址时，会要求输入 Endpoint Password，请使用上方的访问密码。关闭对应的后台命令或终端即可停止外部访问。
```

## 注意事项
- 如果环境中尚未安装 Node.js/npm，请先提醒或协助用户进行安装。
- 获取密码的请求（`https://loca.lt/mytunnelpassword`）必须在运行 LocalTunnel 隧道的**同一台机器上**发起，才能获得正确的密码（基于公网 IP）。
