# 腾讯云 COS：SecretId / SecretKey / Region / Bucket 获取教程

> 适用项目：`image100`（v8 起支持 `STORAGE_BACKEND=cos`）  
> 目标：拿到写入 `.env` 的四个值：`COS_SECRET_ID`、`COS_SECRET_KEY`、`COS_REGION`、`COS_BUCKET`  
> 官方入口：[对象存储控制台](https://console.cloud.tencent.com/cos) · [API 密钥管理](https://console.cloud.tencent.com/cam/capi)

---

## 0. 你最终要填的四项

| 环境变量 | 含义 | 示例（虚构） |
|----------|------|----------------|
| `COS_SECRET_ID` | API 调用者身份 ID | `AKIDxxxxxxxx` |
| `COS_SECRET_KEY` | 与 SecretId 配对的密钥 | `xxxxxxxx`（只显示一次/需保存） |
| `COS_REGION` | 存储桶所在地域简称 | `ap-guangzhou` |
| `COS_BUCKET` | 存储桶完整名称（含 APPID 后缀） | `image100-1250000000` |

对应 `.env` 片段（**项目默认即为 COS**；本机调试可改 `STORAGE_BACKEND=local`）：

```env
STORAGE_BACKEND=cos
COS_SECRET_ID=你的SecretId
COS_SECRET_KEY=你的SecretKey
COS_REGION=ap-shanghai
COS_BUCKET=你的桶名-APPID
```

**安全提醒**：密钥等同账号权限，勿提交到 Git、勿发到群聊；建议用**子账号 + 最小权限**，不要长期把主账号密钥写进开发机。

---

## 1. 注册 / 实名 / 开通 COS（首次）

1. 打开 [腾讯云控制台](https://console.cloud.tencent.com/)，登录账号。  
2. 若未实名：按控制台提示完成实名认证。  
3. 顶部搜索「**对象存储**」或直接打开 [COS 控制台](https://console.cloud.tencent.com/cos)。  
4. 首次进入按提示**开通对象存储服务**（可能涉及计费说明，个人开发常用按量计费即可）。

官方指引：[控制台快速入门](https://cloud.tencent.com/document/product/436/38484)

---

## 2. 创建存储桶 → 得到 `COS_BUCKET` 与 `COS_REGION`

### 2.1 创建

1. 进入 [对象存储 → 存储桶列表](https://console.cloud.tencent.com/cos/bucket)。  
2. 点击 **创建存储桶**。  
3. 建议配置：  
   - **所属地域**：选离你近的，例如「广州」。创建后地域**不可改**。  
   - **名称**：例如 `image100`（系统会自动拼上 `-APPID`）。  
   - **访问权限**：开发期建议 **私有读写**（本项目默认经后端 API 代理读图，不必公开桶）。  
4. 创建完成后进入该桶。

### 2.2 在哪里抄 Region / Bucket

打开该存储桶的 **概览 / 基础配置**（具体菜名以控制台为准）：

| 控制台看到的字段 | 填入环境变量 | 说明 |
|------------------|--------------|------|
| **所属地域**（如「华南地区（广州）」） | `COS_REGION` | 填**地域简称**，广州一般为 `ap-guangzhou`；北京 `ap-beijing`；上海 `ap-shanghai` 等 |
| **名称** / Bucket 名 | `COS_BUCKET` | 必须是**完整名**：`名称-APPID`，例如 `image100-1250000000`，不要只写 `image100` |

地域简称对照可查：[地域和访问域名](https://cloud.tencent.com/document/product/436/6224)

**常见踩坑**：

- `COS_BUCKET` 少了 `-APPID` → SDK 报错或 404。  
- `COS_REGION` 写成中文「广州」或写错成 `gz` → 鉴权/域名错误。  
- 桶在 A 地域、Region 填成 B → 几乎必然失败。

---

## 3. 获取 `COS_SECRET_ID` / `COS_SECRET_KEY`（API 密钥）

密钥在 **访问管理 CAM**，不在 COS 桶详情页里。

1. 打开 [访问管理 → API 密钥管理](https://console.cloud.tencent.com/cam/capi)。  
2. 若是主账号：可 **新建密钥**；列表中可见 **SecretId**，**SecretKey** 通常仅创建时完整展示一次，请立即复制保存。  
3. （推荐）用子账号：  
   - [用户列表](https://console.cloud.tencent.com/cam) 创建子用户 → 勾选「编程访问」→ 生成密钥；  
   - 给子用户授予 COS 相关权限（至少能对该桶读写对象，例如精简策略只允许 `qcs::cos:...:bucket/你的桶/*`）。  

官方说明：[使用永久密钥访问 COS](https://cloud.tencent.com/document/product/436/68282)

填入：

```env
COS_SECRET_ID=AKIDxxxx   # 页面上的 SecretId
COS_SECRET_KEY=xxxx      # 对应的 SecretKey
```

---

## 4. 与本项目对接检查清单

1. `.env` 四项已填，且 `STORAGE_BACKEND=cos`。  
2. 重启 API（及若有 Worker）。  
3. 访问 `GET /api/health`，确认存储相关字段为成功/ok（具体字段以 v8 实现为准）。  
4. 上传一张图，到 COS 控制台该桶的 **文件列表** 中能看到对象。  
5. 前端画布仍能显示图片（经本仓 API 代理读取，私有桶无需改成公有读）。

切换回本地：

```env
STORAGE_BACKEND=local
```

---

## 5. 费用与权限建议（简要）

- COS 按量计费：存储容量 + 请求次数 + 流量；个人练手量一般很小，仍建议设好预算告警。  
- 桶保持**私有读写**，勿为了省事改成「公有读」。  
- 密钥泄露后立刻在 CAM 禁用/删除该密钥并轮换。  

---

## 6. 官方文档速链

| 用途 | 链接 |
|------|------|
| 控制台开通与建桶 | https://cloud.tencent.com/document/product/436/38484 |
| API 密钥管理页 | https://console.cloud.tencent.com/cam/capi |
| 永久密钥说明 | https://cloud.tencent.com/document/product/436/68282 |
| 地域简称 | https://cloud.tencent.com/document/product/436/6224 |
| 存储桶列表 | https://console.cloud.tencent.com/cos/bucket |

若控制台菜单改版，以腾讯云当前 UI 为准；本教程只保证「密钥在 CAM、桶名与地域在 COS 桶概览」这一对应关系。
