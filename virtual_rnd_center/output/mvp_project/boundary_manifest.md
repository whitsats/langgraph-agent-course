# [LEAN_GATE] PROJECT BOUNDARY MANIFEST
## 1. Project Context
- **Product Name**: 轻语录（暂定）
- **Primary Objective**: 为年轻人提供一个极简的社交媒体平台，支持发布图文动态、单向关注好友以及按时间线浏览内容。
- **Target Audience**: 18-25岁年轻用户，偏好轻量、无干扰的社交体验。

## 2. Iterative Pruning & Decision Traceability
| Iteration | Strategic Question | Stakeholder Decision | Impact on Architecture |
| :--- | :--- | :--- | :--- |
| Round 1 | 动态是否只支持纯文字（无图片/视频/链接）？ | **否** → 支持图片 | 需引入单图片上传逻辑，但限制为1张 |
| Round 2 | 是否只允许最多上传1张图片（无多图/无视频）？ | **是** → 单图限制 | 禁止多图上传、视频上传相关代码与存储 |
| Round 3 | 好友互动是否仅限"单向关注（Follow）"？ | **是** → 仅限关注 | 禁止双向好友关系、私信、评论、点赞等接口 |
| Round 4 | 推荐是否仅按时间倒序排列关注动态（无ML推荐）？ | **是** → 时间倒序 | 禁止推荐算法模型、个性化排序逻辑 |
| Round 5 | 注册是否需要邮箱/手机验证？ | **否** → 需要验证 | 必须实现邮箱/手机验证码验证逻辑 |

## 3. Scope Configuration
### 🟢 [X] IN SCOPE (Commitment for V1)
- **Core Feature 1 — 发布图文动态**: 用户可发布纯文字动态或附带最多1张图片的动态。图片上传后存储于本地文件系统，不支持多图、视频、链接嵌入。
- **Core Feature 2 — 单向关注（Follow）**: 用户可关注其他用户，关注后该用户的动态出现在自己的时间线中。无双向好友关系、无粉丝互关要求。
- **Core Feature 3 — 按时间倒序浏览**: 首页时间线展示所关注用户的动态，按发布时间倒序排列。无个性化推荐、无算法排序。
- **Core Feature 4 — 注册与验证**: 用户需提供邮箱或手机号，通过验证码完成注册后方可使用。支持用户名+密码+验证码流程。
- **Essential Middleware**: 本地关系型数据库（SQLite/PostgreSQL）、基本密码哈希（bcrypt）、验证码发送（邮件/SMS API）、本地图片存储。

### 🔴 [ ] OUT OF SCOPE (Deferred/Cut)
- **多图/视频发布**: 增加存储与带宽成本，超出MVP验证需求。
- **评论与点赞**: 社交互动的复杂度太高，V1仅验证"关注+浏览"核心闭环。
- **私信/聊天**: 实时通讯功能需要WebSocket等基础设施，推迟至V2。
- **双向好友关系**: 增加用户关系管理的复杂度，V1仅单向关注。
- **个性化推荐/机器学习**: 算法模型需要大量数据和计算资源，MVP阶段验证内容消费意愿即可。
- **头像/个人资料封面**: 非核心功能，推迟至后续迭代。
- **Scale Target**: 不优化 >1000 CCU（并发用户数），不设计分库分表。

## 4. Constraint & Assumption Matrix
- **Resource Constraint**: 单容器部署，图片存储使用本地磁盘而非云存储（OSS/S3）。
- **Assumed Knowledge**: 用户会使用浏览器/移动端浏览器访问，了解基本的注册登录流程。
- **Assumption**: 初始用户种子数据由开发者手动导入，无自动爬虫或批量注册。

## 5. BANNED FUNCTIONAL ENTITIES & IMPLEMENTATION PATHS
(明确定义在 V1 版本中绝对禁止在代码中实现的【业务功能实体】与【接口路径限制】。这些规则将作为 Code Reviewer 进行语义合规性评估的唯一黄金标准。)

### 🚫 媒体处理限制
- **禁止实现** 视频上传、视频播放、视频转码相关 API 及代码逻辑。
- **禁止实现** 多图上传（一次上传 >1 张图片）的逻辑。
- **禁止实现** 图片裁剪、滤镜、编辑功能。
- **禁止实现** 云存储（OSS/S3/CDN）的文件上传代码；图片存储仅限本地文件系统。
- **BANNED KEYWORDS**: `UploadVideo`, `VideoFile`, `MultiImageUpload`, `ImageEditor`, `OSS`, `S3`, `CDN`, `ImageCropper`, `FileCompressor`

### 🚫 社交互动限制
- **禁止实现** 点赞（Like/LikeButton）、评论（Comment）、分享（Share）的 API 接口及数据库表结构。
- **禁止实现** 双向好友关系（Friendship/MutualFollow）逻辑。
- **禁止实现** 私信/聊天（DM/Chat/Message）的 WebSocket 或 REST 接口。
- **BANNED KEYWORDS**: `Like`, `Comment`, `Share`, `Friendship`, `MutualFollow`, `DM`, `Chat`, `Message`, `Notification`

### 🚫 推荐算法限制
- **禁止实现** 任何基于机器学习的推荐模型、协同过滤、内容标签权重排序逻辑。
- **禁止实现** 用户行为追踪（浏览时长、点击率）用于推荐模型训练。
- **推荐逻辑仅限**：`SELECT * FROM posts WHERE author_id IN (followed_ids) ORDER BY created_at DESC`
- **BANNED KEYWORDS**: `RecommendationModel`, `MLRecommender`, `CollaborativeFiltering`, `UserScore`, `PersonalizedRanking`, `TrendingAlgorithm`

### 🚫 用户与注册限制
- **禁止实现** 免验证注册（即必须走邮箱/手机验证码流程）。
- **禁止实现** OAuth 第三方登录（微信/Google/GitHub）。V1 仅支持邮箱/手机+验证码注册。
- **禁止实现** 密码找回/重置功能（推迟至V2）。
- **BANNED KEYWORDS**: `OAuthLogin`, `SocialLogin`, `PasswordReset`, `NoVerificationRegistration`

## 6. Official Boundary Sign-off
- **Confidence Level**: High
- **Gatekeeper**: AI Pruning Specialist (MVP Gatekeeper)
