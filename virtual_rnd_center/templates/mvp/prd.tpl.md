# [INDUSTRIAL_PRD] BUSINESS REQUIREMENTS DOCUMENT
## 1. Executive Summary
### 1.1 Product Vision
(A concise statement of what the product intends to achieve.)
### 1.2 Success Metrics (KPIs)
- Metric 1: (e.g., User retention > 20% in week 1)
- Metric 2: (e.g., Latency < 200ms)

## 2. User Personas & Scenarios
### 2.1 Primary Persona: [Name/Type]
- **Goals**: ...
- **Pain Points**: ...
### 2.2 Key User Scenarios
- **Scenario A**: (Step-by-step business flow)

## 3. Functional Requirements (The "What")
### 3.1 Feature Set Matrix
| ID | Feature Name | Description | Priority |
| :--- | :--- | :--- | :--- |
| FR-01 | ... | ... | P0 |
| FR-02 | ... | ... | P1 |

## 4. Business Rules & Logic
- **Rule 1**: (e.g., "Anonymous posts expire after 24 hours")
- **Rule 2**: (e.g., "Max post length: 280 chars")

## 5. Non-Functional Requirements
- **Performance**: ...
- **Security**: (Basic requirements, not implementation)
- **Usability**: ...

## 6. Business Risks & Mitigation
(Identify 2-3 business-level risks and how the MVP mitigates them.)

## 7. SCOPE BOUNDARY & FUNCTIONAL RESTRICTIONS
(将《边界宣言》中的 OOS（出界）决定翻译为具体的【架构与代码功能限制规范】。以清晰的文字形式约束开发边界，供 Code Reviewer 审计评估。
例如：
- 禁止设计/开发任何处理 likes、comments、shares 的 API 接口。
- 数据库结构绝对禁止包含 likes、comments、friendship 相关的表。
- 主路由禁止注册 /api/upload 或 /api/posts/{id}/like 相关的 Endpoint。
- 禁止编写任何实际的业务逻辑来实现这些出界功能。)
