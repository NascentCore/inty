# **使用 Stripe 实现稳健型 SaaS 订阅模式的架构蓝图**

### **摘要**

本报告详细阐述了为 SaaS（软件即服务）网络应用（例如 AI 陪伴服务）实施周期性订阅模式的权威、最稳定且最典型的技术架构。推荐的解决方案并非单一的 Stripe 产品，而是三个核心组件的战略组合：以 **Stripe Billing** 作为订阅逻辑引擎，以 **Stripe Checkout** 作为预构建的安全用户界面用于初始订阅注册，以及 **Stripe Customer Portal** 用于用户自助服务管理。这种方法最大限度地提高了安全性、可靠性和用户转化率，同时最大限度地减少了开发开销。该架构的支柱是建立在 Stripe Webhooks 之上的事件驱动系统，确保了应用程序的内部状态与 Stripe 的计费事件保持完美同步。我们将通过一个五阶段的实施计划，涵盖定价模型设置、新订阅用户旅程、强大的后端 Webhook 处理、订阅后管理以及支持该系统所必需的数据库模式。

---

### **I. 基础架构：选择正确的 Stripe 组件**

本节阐述了我们所选技术栈背后的“原因”。我们将论证，对于绝大多数 SaaS 应用而言，自定义构建支付流程是一种不必要的风险和工程负担。最优策略是利用 Stripe 预构建的托管解决方案。

#### **1.1 Stripe Billing：订阅引擎**

Stripe Billing 是一个非可视化的后端引擎，为整个订阅生命周期提供动力 1。它不是一个 UI 组件，而是一套用于管理周期性支付的 API 和逻辑。其核心职责包括处理周期性发票的创建、管理订阅状态（例如 active、past\_due、canceled）、处理续订、计算计划变更的按比例分配费用以及管理试用期 1。通过使用 Stripe Billing，应用可以卸载周期性支付逻辑的巨大复杂性。应用程序无需构建自己的定时任务（cron jobs）或状态机来跟踪何时向客户收费；这正是 Billing 的根本目的 5。

#### **1.2 Stripe Checkout：安全、高转化的入口**

Stripe Checkout 是一个为优化转化率而设计的预构建、由 Stripe 托管的支付页面 3。它作为用户输入支付详情和发起订阅的主要界面。其关键优势在于：

* **降低 PCI 合规范围：** 敏感的持卡人数据直接在 Stripe 的域名上输入，绝不会触及我们的应用服务器。这极大地简化了 PCI 合规性 8。  
* **转化率优化：** Stripe 持续对 Checkout 页面进行 A/B 测试和优化，以实现最大转化率，集成了地址自动完成、实时卡片验证和本地化支付方式等功能 3。这种级别的优化对于单个公司来说是难以复制的。  
* **全球支付方式：** Checkout 提供对超过 100 种支付方式的开箱即用支持，这些支付方式可以从 Dashboard 中启用，无需额外代码，从而轻松实现国际扩张 7。

对于新订阅而言，Checkout 是最稳健和安全的方法。它是通往由 Stripe Billing 管理的订阅的“前门” 1。

#### **1.3 Stripe Customer Portal：赋能自助服务并减少客户流失**

Customer Portal 是另一个由 Stripe 托管的页面，允许经过身份验证的用户管理他们*现有*的订阅 12。用户可以更新他们的支付方式、查看发票历史、在不同计划之间切换（例如，从“专业版月度”升级到“专业版年度”），以及取消他们的订阅，所有这些都无需联系客户支持 13。

Customer Portal 是一个关键的运营工具。它直接减少了支持工单的数量，并赋予用户权力，从而提高了客户满意度。它还提供了减少客户流失的功能，例如在用户取消时提示输入原因或提供挽留优惠券 13。

#### **1.4 架构协同：一个统一的系统**

一个典型的用户流程如下：用户在应用的定价页面上点击“订阅” \-\> 应用后端创建一个 **Checkout Session** \-\> 用户被重定向到 **Stripe Checkout** 页面进行支付 \-\> 成功后，一个订阅在 **Stripe Billing** 中被创建 \-\> 用户稍后可以在应用中点击“管理订阅” \-\> 后端创建一个 **Portal Session** \-\> 用户被重定向到 **Stripe Customer Portal** 来管理上一步创建的订阅。

这种组合形成了一个完整的端到端系统，其中我们应用的主要职责是启动这些流程并通过 Webhooks 对状态变化做出反应，而不是构建用于收款和管理的复杂 UI 和逻辑。

选择 Checkout 和 Portal 而非基于 Elements 的自定义解决方案，这不仅仅是一个技术选择，更是一个战略性的商业决策。研究一致强调了 Stripe 的预构建、托管组件：Checkout 7、定价表 16 和 Customer Portal 12。这些组件不仅是便利工具，更是功能丰富、经过优化的产品 3。替代方案是使用 Stripe Elements 3，它提供 UI 组件来在您自己的网站上构建自定义表单，但这需要更多的开发工作，并将更多的安全（PCI）和设计责任放在开发者身上。通过选择预构建的路径，初创公司实际上是将整个支付和订阅管理的 UX“外包”给了 Stripe 的专业团队。这释放了有限的工程资源，使其能够专注于核心产品（AI 陪伴应用），这才是初创公司的真正竞争优势。其连锁反应是更快的上市时间和更低的持续维护负担，直接影响公司的敏捷性和资金消耗率。

---

### **II. 阶段一：业务与定价建模**

在编写任何代码之前，必须将业务模型转化为 Stripe 的数据结构。这是一个基础步骤，如果做得正确，将为未来的定价变更提供灵活性。

#### **2.1 定义 Product 和 Price 对象**

在 Stripe 的模型中，Product 是您销售的服务（例如，“专业版计划”），而 Price 是您为该 Product 收取多少费用以及收费频率（例如，“每月 15 美元”）5。这种分离至关重要。

对于 talkie-ai.com 的模型，我们将在 Stripe Dashboard 中创建两个 Product：“Premium”和“Pro”。

* 对于“Premium” Product，我们将创建两个 Price：一个用于月度计费，一个用于年度计费。  
* 对于“Pro” Product，我们也将创建两个 Price：一个月度，一个年度。

对于每个创建的 Price，我们必须保存其唯一的 ID（例如，price\_1M...）。这些 ID 是我们应用 UI 和 Stripe 后端之间的链接 10。

#### **2.2 价格管理最佳实践**

* **不可变性：** Price 对象是不可变的。您不能更改现有 Price 的金额或货币。要更改定价，您必须创建一个*新*的 Price 对象并将其附加到 Product 上，然后更新您的应用程序以使用新的 Price ID 14。  
* **存储 Price ID：** 这些 ID 应存储在您应用的配置文件或环境变量中，而不是直接硬编码在前端。这使得更新更加容易。  
* **可选：使用定价表组件：** Stripe 提供了一个可嵌入的、无代码的 Pricing Table 组件，可以在 Dashboard 中配置以显示您的产品和价格。点击此表上的计划会自动将用户引导至该价格的 Checkout 会话，从而极大地简化了前端集成 1。

---

### **III. 阶段二：核心用户旅程 \- 创建新订阅**

本节详细介绍了用户首次订阅的技术流程。

#### **3.1 新订阅流程的序列图**

一个典型的交互序列如下：

1. **用户** 在前端点击“订阅”。  
2. **前端** 向后端 /create-checkout-session 端点发送一个带有选定 priceId 的 POST 请求。  
3. **后端** 接收请求，验证用户身份，并调用 Stripe API stripe.checkout.sessions.create()。  
4. **Stripe API** 返回一个带有唯一 url 的会话对象。  
5. **后端** 将此 url 发送回前端。  
6. **前端** 将用户的浏览器重定向到 Stripe Checkout url。  
7. **用户** 在 Stripe 托管的页面上完成支付。  
8. **Stripe** 将用户重定向回会话创建时指定的 success\_url。  
9. **Stripe**（异步地）向后端的 Webhook 端点发送一个 checkout.session.completed Webhook 事件。

#### **3.2 后端：创建 Checkout Session**

这是发起订阅最关键的服务器端端点。我们将提供一个完整的 Node.js (Express) 代码示例。

**stripe.checkout.sessions.create() 的关键参数：**

* mode: 'subscription': 这是强制性的。它告诉 Checkout 创建一个周期性订阅，而不是一次性支付 9。  
* line\_items: \[{ price: priceId, quantity: 1 }\]: 指定用户订阅的 Price 10。  
* success\_url: 用户成功支付后重定向到的 URL。包含 {CHECKOUT\_SESSION\_ID} 模板变量（.../success?session\_id={CHECKOUT\_SESSION\_ID}）是至关重要的，这样前端可以显示个性化的成功消息 10。  
* cancel\_url: 如果用户取消流程，他们将被发送到的 URL 10。  
* customer: 如果用户已在我们的应用中注册，并且我们有相应的 Stripe Customer ID，我们应该在这里传递它。这将订阅链接到他们现有的记录 20。如果未提供，Stripe 将创建一个新的 Customer 对象 22。  
* client\_reference\_id: 这是一个最佳实践。我们应该在这里传递我们应用的内部 user\_id。此 ID 将出现在 Webhook 事件中，使得在无需额外查找步骤的情况下，将 Stripe 事件与我们数据库中的用户进行核对变得容易 22。

#### **3.3 前端：重定向到 Checkout**

客户端 JavaScript 非常直接。它向后端端点发出一个 fetch 请求，接收包含会话 URL 的 JSON 响应，然后将 window.location 设置为该 URL 23。

#### **3.4 处理 success\_url 重定向**

一个重要的区别是：用户到达 success\_url 表示他们*完成*了结账流程，但这**不**保证支付成功或订阅已激活。网络问题可能会阻止 Webhook 到达，或者支付方式可能会异步失败。

正确的逻辑是：成功页面应显示一个通用的“感谢您！我们正在处理您的订阅...”消息。它**不应**授予对高级功能的访问权限。访问权限仅在成功处理相应的 Webhook 事件后授予。这是系统可靠性的一个关键点。

---

### **IV. 阶段三：后端引擎 \- 掌握 Webhooks 进行生命周期管理**

Webhooks 是从 Stripe 到我们应用程序的异步通信渠道。它们是可靠订阅系统的基础。

#### **4.1 Webhooks 的关键作用**

订阅事件发生在很长一段时间内（每月续订、取消、支付失败）。应用程序不能持续轮询 Stripe API 来检查状态变化。Webhooks 实时将这些变化推送给我们，从而实现事件驱动的架构 10。未能正确实施 Webhooks 是 Stripe 集成中最常见的失败点。它会导致用户支付失败但仍保留访问权限，或者他们的订阅续订但访问权限未被延长等情况。

#### **4.2 配置和保护您的 Webhook 端点**

* **设置：** 在您的应用中创建一个专用的公共端点（例如，/api/webhooks/stripe），接受 POST 请求 26。  
* **签名验证：** Stripe 会用一个密钥对它发送的每个 Webhook 事件进行签名。您的端点**必须**在每个传入请求上验证此签名。这可以防止攻击者向您的端点发送伪造事件以授予自己免费访问权限。Stripe 库提供了帮助函数来简化此验证过程 26。任何没有有效签名的请求都必须以 400 Bad Request 状态拒绝。

#### **4.3 幂等性：确保每个事件只被处理一次**

由于网络状况，Stripe 可能会多次发送同一个 Webhook 事件。如果我们的 invoice.paid 处理程序只是简单地为用户的访问权限增加一个月，那么接收到同一个事件两次将错误地授予他们两个月的访问权限 27。

我们的 Webhook 处理程序必须是幂等的，这意味着多次处理同一个事件与处理一次具有相同的效果 28。

**实施策略：**

1. 当收到 Webhook 事件时，提取其唯一的 event.id。  
2. 在处理之前，检查数据库表（例如，processed\_events）以查看此 event.id 是否已被记录。  
3. 如果已被记录，立即向 Stripe 返回一个 200 OK 的成功响应以确认收到，但不再重新运行业务逻辑。  
4. 如果尚未记录，开始处理业务逻辑。将整个过程包装在数据库事务中。首先，将 event.id 插入到 processed\_events 中。然后，执行业务逻辑（例如，更新 subscriptions 表）。如果任何环节失败，事务将回滚，event.id 不会被保存，从而允许未来的重试成功。  
5. 完成后，返回一个 200 OK 响应。

#### **4.4 处理关键订阅事件**

本节将包含我们后端的核心逻辑。我们将详细说明最重要的事件以及对每个事件应采取的确切行动。提供一个规范性的“操作手册”来指导 Webhook 处理程序的构建，将抽象的事件处理概念转化为具体的指令集，从而将特定的触发器映射到特定的、必需的业务逻辑。这直接满足了用户对“稳定和典型”解决方案的需求，通过编纂管理订阅生命周期的标准、经过实战检验的逻辑，防止了诸如未能正确授予或撤销访问权限等常见错误。

| Webhook 事件 | 触发时机 | 需要提取的关键数据 | 必需的后端操作 |
| :---- | :---- | :---- | :---- |
| checkout.session.completed | 用户成功完成新订阅的 Stripe Checkout 流程。 | id, client\_reference\_id, customer, subscription, metadata | 1\. 使用 client\_reference\_id（您的内部 user\_id）来识别用户。 2\. 在您的本地 subscriptions 表中创建一个新记录。 3\. 存储 customer (Stripe Customer ID) 和 subscription (Stripe Subscription ID) 到数据库中，并与用户关联。 4\. **此时不要授予访问权限。** 等待 invoice.paid 事件。 |
| invoice.paid | 订阅发票成功支付。这在新订阅时立即发生，并在每次后续续订时发生。 | customer, subscription, billing\_reason, period\_end | 1\. 通过 customer ID 找到用户。 2\. 验证 billing\_reason 是 subscription\_create 或 subscription\_cycle 30。 3\. 更新本地订阅记录：将 status 设置为 active，并将 current\_period\_end 更新为新的 period\_end 时间戳。 4\. **这是授予或延长高级功能访问权限的事件。** |
| invoice.payment\_failed | 尝试支付订阅发票失败（例如，卡已过期）。 | customer, subscription, next\_payment\_attempt | 1\. 通过 customer ID 找到用户。 2\. 将本地订阅记录的 status 更新为 past\_due。 3\. 触发应用内通知和/或向用户发送电子邮件，告知他们支付失败，并引导他们到客户门户更新支付方式。Stripe 的智能重试功能可能会重新尝试支付 4。 |
| customer.subscription.updated | 订阅发生变更（例如，用户通过客户门户升级/降级）。 | id, customer, items.data.price.id, status, cancel\_at\_period\_end | 1\. 通过其 id 找到订阅。 2\. 使用新的 price\_id、status 和 cancel\_at\_period\_end 标志更新本地记录。 3\. 根据与新 price\_id 关联的计划调整用户的功能访问权限。 |
| customer.subscription.deleted | 订阅被取消（无论是立即取消还是在计费周期结束时取消）。 | id, customer, status | 1\. 通过其 id 找到订阅。 2\. 如果订阅被立即取消，将本地 status 更新为 canceled 并立即撤销访问权限。 3\. 如果是计划在周期结束时取消（cancel\_at\_period\_end 为 true），customer.subscription.updated 事件已经设置了该标志。这个 deleted 事件确认了周期的结束。现在将本地 status 更新为 canceled 并撤销访问权限。 |

---

### **V. 阶段四：使用 Customer Portal 进行订阅后管理**

此阶段涵盖了如何在用户初次注册后，让他们能够控制自己的订阅。

#### **5.1 在 Dashboard 中配置门户功能**

导航至 Stripe Dashboard \-\> 设置 \-\> Billing \-\> Customer portal 12。

**关键配置：**

* **产品和价格：** 指定用户可以在哪些计划之间切换 14。  
* **取消策略：** 允许用户立即取消或在计费周期结束时取消。启用“取消原因”收集功能 13。  
* **支付方式：** 允许用户更新他们的支付方式（此项应始终启用）。  
* **重定向：** 设置一个默认的 return\_url，将用户送回您的应用程序的账户页面 13。  
* **品牌化：** 使用您公司的徽标和颜色自定义门户 13。

#### **5.2 后端：创建 Portal Session**

这是一个安全的服务器端端点，为特定用户生成一个临时的、唯一的 URL 以访问门户。

**逻辑：**

1. 该端点必须受到保护；只有您应用的已认证用户才能访问。  
2. 从您的数据库中检索已登录用户的 stripe\_customer\_id。  
3. 使用 customer ID 和 return\_url 调用 stripe.billingPortal.sessions.create() 14。  
4. 将 session.url 返回给前端。

#### **5.3 前端：提供对门户的访问**

在您的应用的用户账户或设置页面中，添加一个“管理订阅”或“管理账单”按钮。当点击时，此按钮会触发对上述后端端点的请求，并将用户重定向到返回的门户 URL 14。

---

### **VI. 阶段五：数据库设计与数据同步**

订阅状态的本地副本对于性能和可靠性至关重要。您的应用不应该在每次用户请求页面时都进行实时 API 调用来检查他们是否有访问权限。

#### **6.1 设计您的订阅模式**

应用程序需要一种快速、可靠的方式来回答这个问题：“该用户现在是否有权访问功能 X？” 在每个请求上调用 Stripe API 是缓慢、昂贵的，并且增加了一个失败点（如果 Stripe API 宕机，您的应用也会宕机）。因此，需要一个用户订阅状态的本地缓存 31。下表定义了为做出授权决策而需要本地存储的*最少基本数据*。它作为应用程序事实来源的蓝图，通过 Webhooks 与 Stripe 的事实来源保持同步。提供此模式可以为开发者节省大量时间，并防止存储过多或过少信息等常见错误。

| 表名 | 列名 | 数据类型 | 备注 |
| :---- | :---- | :---- | :---- |
| users | id | UUID / BIGINT | 您的用户表的主键。 |
|  | email | VARCHAR | 用户的电子邮件地址。 |
|  | ... | ... | 其他用户个人资料字段。 |
|  | stripe\_customer\_id | VARCHAR | 指向 Stripe Customer 对象的外键。已索引以进行快速查找。唯一。 |
| subscriptions | id | UUID / BIGINT | 此表的主键。 |
|  | user\_id | UUID / BIGINT | 链接到 users 表的外键。 |
|  | stripe\_subscription\_id | VARCHAR | Stripe Subscription 对象的 ID (sub\_...)。已索引且唯一。 |
|  | status | VARCHAR / ENUM | 订阅状态的本地副本（例如，active, trialing, past\_due, canceled）。 |
|  | stripe\_price\_id | VARCHAR | 用户当前订阅的 Price 的 ID。决定了他们的计划/等级。 |
|  | current\_period\_end | TIMESTAMP | 当前付费周期结束的时间戳。用于向用户显示下一次续订时间。 |
|  | cancel\_at\_period\_end | BOOLEAN | 标志，指示用户是否选择在当前周期结束时取消。 |
|  | created\_at | TIMESTAMP | 创建时间戳。 |
|  | updated\_at | TIMESTAMP | 最后更新时间戳。 |

#### **6.2 同步过程**

需要重申的是，更新 subscriptions 表的*唯一*机制是通过经过验证的 Webhook 处理程序。应用程序代码的任何其他部分都不应写入此表。这强制执行了一个单一的数据流：**Stripe \-\> Webhook 处理程序 \-\> 本地数据库**。这确保了数据的完整性。

#### **6.3 授权功能访问**

当用户尝试访问高级功能时，应用程序的授权逻辑应该很简单：

1. 查询本地 subscriptions 表以获取当前用户的信息。  
2. 检查是否存在 status \= 'active' 的记录。  
3. （可选）检查 current\_period\_end 是否在未来。

这是一个快速的本地数据库查询，性能高，并且不依赖于请求时任何外部服务的可用性。

---

### **VII. 结论：测试、上线与运营最佳实践**

#### **7.1 利用 Stripe 的测试模式和工具**

* **测试 API 密钥：** 在所有开发过程中使用测试模式的 API 密钥 8。  
* **测试卡：** 使用 Stripe 提供的测试卡号来模拟成功支付、失败支付和 3D 安全认证流程 23。  
* **Stripe CLI：** 使用 Stripe CLI 通过将事件从 Stripe 转发到您的开发机器来本地测试 Webhooks。这是在不部署到公共服务器的情况下调试 Webhook 处理程序的不可或缺的工具 18。  
* **测试时钟（高级）：** 要模拟时间的流逝（例如，测试订阅续订、试用期满和催款周期），请使用 Stripe 的测试时钟功能 32。

#### **7.2 上线清单**

1. 在您的环境变量中将测试 API 密钥切换为实时 API 密钥。  
2. 在 Stripe Dashboard 的实时模式下重新创建您的 Products 和 Prices。  
3. 为实时模式配置客户门户。  
4. 在 Dashboard 中创建一个新的实时模式 Webhook 端点，并将其指向您的生产服务器 URL。  
5. 确保实时模式的 Webhook 签名密钥已在您的生产服务器上正确配置。  
6. 使用真实的支付方式在实时模式下最后一次彻底测试整个流程。

#### **7.3 监控与维护**

* 为您的 Webhook 端点设置监控和警报。来自此端点的高 5xx 错误率是一个需要立即关注的关键问题。  
* 定期在 Stripe Dashboard 中审查失败的支付，以识别支付方式或欺诈模式的潜在问题。  
* 保持 Stripe 客户端库和 API 版本的更新，以受益于新功能和安全改进。

#### **Works cited**

1. Billing | Stripe Documentation, accessed October 26, 2025, [https://docs.stripe.com/billing](https://docs.stripe.com/billing)  
2. Stripe Documentation, accessed October 26, 2025, [https://docs.stripe.com/](https://docs.stripe.com/)  
3. Stripe Checkout | Checkout Pages for Your Website, accessed October 26, 2025, [https://stripe.com/payments/checkout](https://stripe.com/payments/checkout)  
4. How subscriptions work \- Stripe Documentation, accessed October 26, 2025, [https://docs.stripe.com/billing/subscriptions/overview](https://docs.stripe.com/billing/subscriptions/overview)  
5. Build a subscriptions integration \- Stripe Documentation, accessed October 26, 2025, [https://docs.stripe.com/billing/subscriptions/build-subscriptions?platform=web\&ui=elements](https://docs.stripe.com/billing/subscriptions/build-subscriptions?platform=web&ui=elements)  
6. Build a subscriptions integration \- Stripe Documentation, accessed October 26, 2025, [https://docs.stripe.com/billing/subscriptions/build-subscriptions?platform=react-native](https://docs.stripe.com/billing/subscriptions/build-subscriptions?platform=react-native)  
7. Stripe Checkout | Stripe Documentation, accessed October 26, 2025, [https://docs.stripe.com/payments/checkout](https://docs.stripe.com/payments/checkout)  
8. How to integrate a payment gateway into a website \- Stripe, accessed October 26, 2025, [https://stripe.com/resources/more/how-to-integrate-a-payment-gateway-into-a-website](https://stripe.com/resources/more/how-to-integrate-a-payment-gateway-into-a-website)  
9. How Checkout works \- Stripe Documentation, accessed October 26, 2025, [https://docs.stripe.com/payments/checkout/how-checkout-works](https://docs.stripe.com/payments/checkout/how-checkout-works)  
10. Build a subscriptions integration \- Stripe Documentation, accessed October 26, 2025, [https://docs.stripe.com/billing/subscriptions/build-subscriptions](https://docs.stripe.com/billing/subscriptions/build-subscriptions)  
11. Recurring payments | Stripe Documentation, accessed October 26, 2025, [https://docs.stripe.com/recurring-payments](https://docs.stripe.com/recurring-payments)  
12. Set up the customer portal | Stripe Documentation, accessed October 26, 2025, [https://docs.stripe.com/no-code/customer-portal](https://docs.stripe.com/no-code/customer-portal)  
13. Configure the customer portal | Stripe Documentation, accessed October 26, 2025, [https://docs.stripe.com/customer-management/configure-portal](https://docs.stripe.com/customer-management/configure-portal)  
14. Integrate the customer portal with the API | Stripe Documentation, accessed October 26, 2025, [https://docs.stripe.com/customer-management/integrate-customer-portal](https://docs.stripe.com/customer-management/integrate-customer-portal)  
15. Billing customer portal \- Stripe: Help & Support, accessed October 26, 2025, [https://support.stripe.com/questions/billing-customer-portal](https://support.stripe.com/questions/billing-customer-portal)  
16. Subscriptions \- Stripe Documentation, accessed October 26, 2025, [https://docs.stripe.com/subscriptions](https://docs.stripe.com/subscriptions)  
17. Design a subscriptions integration \- Stripe Documentation, accessed October 26, 2025, [https://docs.stripe.com/billing/subscriptions/design-an-integration](https://docs.stripe.com/billing/subscriptions/design-an-integration)  
18. Build a subscriptions integration \- Stripe Documentation, accessed October 26, 2025, [https://docs.stripe.com/billing/subscriptions/build-subscriptions?platform=web\&ui=embedded-components](https://docs.stripe.com/billing/subscriptions/build-subscriptions?platform=web&ui=embedded-components)  
19. dzlau/stripe-supabase-saas-template \- GitHub, accessed October 26, 2025, [https://github.com/dzlau/stripe-supabase-saas-template](https://github.com/dzlau/stripe-supabase-saas-template)  
20. Stripe Checkout Session flow \- Medium, accessed October 26, 2025, [https://medium.com/@surajit.das0320/stripe-checkout-session-flow-b83bd87d22e2](https://medium.com/@surajit.das0320/stripe-checkout-session-flow-b83bd87d22e2)  
21. Stripe create-checkout-session not loading \- node.js \- Stack Overflow, accessed October 26, 2025, [https://stackoverflow.com/questions/65637916/stripe-create-checkout-session-not-loading](https://stackoverflow.com/questions/65637916/stripe-create-checkout-session-not-loading)  
22. Create a Checkout Session | Stripe API Reference, accessed October 26, 2025, [https://docs.stripe.com/api/checkout/sessions/create?lang=node](https://docs.stripe.com/api/checkout/sessions/create?lang=node)  
23. stripe-samples/checkout-single-subscription: Learn how to combine Checkout and Billing for fast subscription pages \- GitHub, accessed October 26, 2025, [https://github.com/stripe-samples/checkout-single-subscription](https://github.com/stripe-samples/checkout-single-subscription)  
24. Help with Stripe Checkout Session in Node.js and React : r/reactjs \- Reddit, accessed October 26, 2025, [https://www.reddit.com/r/reactjs/comments/1fma9jc/help\_with\_stripe\_checkout\_session\_in\_nodejs\_and/](https://www.reddit.com/r/reactjs/comments/1fma9jc/help_with_stripe_checkout_session_in_nodejs_and/)  
25. Using webhooks with subscriptions | Stripe Documentation, accessed October 26, 2025, [https://docs.stripe.com/billing/subscriptions/webhooks](https://docs.stripe.com/billing/subscriptions/webhooks)  
26. Receive Stripe events in your webhook endpoint, accessed October 26, 2025, [https://docs.stripe.com/webhooks](https://docs.stripe.com/webhooks)  
27. Building resilient webhook handlers in AWS: Implementing DLQs for Stripe events, accessed October 26, 2025, [https://stripe.dev/blog/building-resilient-webhook-handlers-aws-dlqs-stripe-events](https://stripe.dev/blog/building-resilient-webhook-handlers-aws-dlqs-stripe-events)  
28. Advanced error handling | Stripe Documentation, accessed October 26, 2025, [https://docs.stripe.com/error-low-level](https://docs.stripe.com/error-low-level)  
29. How to Implement Webhook Idempotency \- Hookdeck, accessed October 26, 2025, [https://hookdeck.com/webhooks/guides/implement-webhook-idempotency](https://hookdeck.com/webhooks/guides/implement-webhook-idempotency)  
30. Stripe Webhook events Renewal of subscription \- Stack Overflow, accessed October 26, 2025, [https://stackoverflow.com/questions/22601521/stripe-webhook-events-renewal-of-subscription](https://stackoverflow.com/questions/22601521/stripe-webhook-events-renewal-of-subscription)  
31. Suggested database architecture for my first SaaS with Stripe? \- Indie Hackers, accessed October 26, 2025, [https://www.indiehackers.com/post/suggested-database-architecture-for-my-first-saas-with-stripe-7b6ff9927f](https://www.indiehackers.com/post/suggested-database-architecture-for-my-first-saas-with-stripe-7b6ff9927f)  
32. Integrate a SaaS business on Stripe \- Stripe Documentation, accessed October 26, 2025, [https://docs.stripe.com/saas](https://docs.stripe.com/saas)
