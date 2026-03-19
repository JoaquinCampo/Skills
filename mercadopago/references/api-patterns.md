# MercadoPago Integration Patterns & Best Practices

> Research compiled 2026-03-17 from official MP documentation, Node SDK source, and community patterns.

---

## 1. Checkout Pro vs Checkout API vs Checkout Bricks

### Checkout Pro (Recommended for our use case)
- **What it is:** Pre-built hosted checkout. You create a "preference" server-side, get back an `init_point` URL. The buyer is redirected to MercadoPago's domain to complete payment.
- **Best for:** Payment links via WhatsApp/Instagram, quick integrations, maximum payment method coverage.
- **Payment methods:** Credit/debit cards, Rapipago, Pago Facil, Mercado Pago Wallet, Installments without Card.
- **Key advantage for us:** The `init_point` URL can be sent directly in WhatsApp/Instagram messages. No frontend SDK needed.
- **Integration effort:** Low.
- **Countries:** AR, BR, CL, CO, MX, PE, UY.

### Checkout Bricks
- **What it is:** Modular, embeddable UI components (Payment Brick, Card Payment Brick, Status Screen Brick, Wallet Brick, Brand Brick).
- **Best for:** Custom in-site checkout experiences where you want MP's pre-built UI but embedded in your own page.
- **Key features:** 3DS 2.0 auth, anti-fraud, saved cards, PCI-simplified.
- **Integration effort:** Medium.
- **Not suitable for us:** Requires embedding in a webpage; cannot send via messaging.

### Checkout API (via Orders)
- **What it is:** Full API control. You build the entire checkout UI, tokenize cards yourself via MercadoPago.js, and call the API.
- **Best for:** Fully custom checkout pages, maximum control over UX.
- **Key features:** Manual or automatic processing modes, total customization.
- **Integration effort:** High.
- **Not suitable for us:** Overkill for a chat-based flow. Requires custom frontend.

### Decision for Seller-Agent
**Use Checkout Pro.** Create preferences server-side, send the `init_point` URL via WhatsApp/Instagram. The buyer clicks the link, pays on MP's hosted page, and we get webhook notifications.

---

## 2. WhatsApp/Instagram Commerce Integration Pattern

### The Flow
```
1. Customer chats with bot on WhatsApp/Instagram
2. Bot identifies product(s) customer wants to buy
3. Backend creates a MercadoPago Preference (server-side)
4. Backend extracts `init_point` from the response
5. Bot sends the `init_point` URL as a message to the customer
6. Customer taps link -> redirected to MP hosted checkout
7. Customer pays (card, cash, wallet, etc.)
8. MP sends webhook to our backend with payment status
9. Bot sends confirmation message to customer
```

### Creating the Preference (Node.js SDK)
```typescript
import { MercadoPagoConfig, Preference } from 'mercadopago';

const client = new MercadoPagoConfig({
  accessToken: '<MERCHANT_ACCESS_TOKEN>',
  options: { timeout: 5000 }
});

const preference = new Preference(client);

const result = await preference.create({
  body: {
    items: [{
      id: 'product-123',
      title: 'Blue T-Shirt Size M',
      quantity: 1,
      unit_price: 2500.00,
      currency_id: 'ARS'
    }],
    // Link this payment to our internal order
    external_reference: 'order-uuid-here',
    // Where MP sends webhook notifications
    notification_url: 'https://api.ourplatform.com/webhooks/mercadopago?source_news=webhooks',
    // Where user goes after payment
    back_urls: {
      success: 'https://ourplatform.com/payment/success',
      failure: 'https://ourplatform.com/payment/failure',
      pending: 'https://ourplatform.com/payment/pending'
    },
    auto_return: 'approved',
    // Set expiration for the payment link
    expires: true,
    date_of_expiration: '2026-03-18T23:59:59.000-03:00',
    // For marketplace model: charge our platform fee
    marketplace_fee: 250.00,
    // binary_mode: true = only approved/rejected (no pending)
    // binary_mode: false = allows pending states (default)
    binary_mode: false,
    statement_descriptor: 'SELLER AGENT',
  }
});

// This is the payment link to send via WhatsApp/Instagram
const paymentLink = result.init_point;
// For testing, use:
const sandboxLink = result.sandbox_init_point;
```

### Key Fields in PreferenceResponse
| Field | Description |
|-------|-------------|
| `id` | Preference ID |
| `init_point` | **Production payment URL** (send this to customers) |
| `sandbox_init_point` | **Sandbox payment URL** (for testing) |
| `collector_id` | Merchant's MP account ID |
| `external_reference` | Your internal order/reference ID |
| `date_created` | When preference was created |

### WhatsApp Message Example
```
Your order is ready! Here's your payment link:
[Pay ARS $2,500.00](https://www.mercadopago.com.ar/checkout/v1/redirect?pref_id=XXX)

This link expires in 24 hours. You can pay with credit/debit card, cash at Rapipago/Pago Facil, or Mercado Pago wallet.
```

---

## 3. Multi-Tenant Architecture

### The Challenge
Each merchant on our SaaS platform has their own MercadoPago account. We need to:
1. Create preferences using each merchant's credentials
2. Receive webhooks for all merchants
3. Collect platform fees/commissions

### Architecture Options

#### Option A: OAuth + Marketplace Model (Recommended)
```
Platform (us) -> OAuth connects -> Merchant MP accounts
                                      |
                  Uses merchant's access_token to create preferences
                  Charges marketplace_fee on each transaction
```

- Platform has one MP application (one `client_id`/`client_secret`)
- Each merchant authorizes our app via OAuth
- We store each merchant's `access_token` (180-day expiry) and `refresh_token`
- When creating preferences, we use the merchant's `access_token`
- We set `marketplace_fee` on each preference to collect our commission

#### Option B: Direct Credential Storage (Simpler but less secure)
```
Each merchant provides their access_token directly
We store and use it to create preferences
```

- Simpler but less professional
- No OAuth flow, merchants paste their credentials
- Cannot collect fees automatically (need separate arrangement)
- Not recommended for production SaaS

### Database Schema (for Option A)
```sql
CREATE TABLE merchant_mp_connections (
  id UUID PRIMARY KEY,
  merchant_id UUID NOT NULL REFERENCES merchants(id),
  mp_user_id BIGINT NOT NULL,          -- MercadoPago user ID
  access_token TEXT NOT NULL,           -- Encrypted at rest
  refresh_token TEXT NOT NULL,          -- Encrypted at rest
  token_expires_at TIMESTAMPTZ NOT NULL,
  scopes TEXT[],                        -- e.g., ['read', 'write', 'offline_access']
  is_active BOOLEAN DEFAULT true,
  connected_at TIMESTAMPTZ DEFAULT NOW(),
  last_refreshed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Multi-tenant Preference Creation
```typescript
async function createPaymentForMerchant(merchantId: string, items: Item[]) {
  const connection = await db.merchantMpConnections.findFirst({
    where: { merchantId, isActive: true }
  });

  if (!connection) throw new Error('Merchant not connected to MercadoPago');

  // Check if token needs refresh
  if (connection.tokenExpiresAt < new Date()) {
    await refreshMerchantToken(connection);
  }

  // Create MP client with THIS merchant's access token
  const client = new MercadoPagoConfig({
    accessToken: decrypt(connection.accessToken),
    options: { timeout: 5000 }
  });

  const preference = new Preference(client);
  return preference.create({
    body: {
      items,
      marketplace_fee: calculatePlatformFee(items),
      notification_url: `https://api.ourplatform.com/webhooks/mercadopago?merchant=${merchantId}`,
      external_reference: `${merchantId}:${orderId}`,
    }
  });
}
```

---

## 4. OAuth Flow for Connecting Merchants

### Step 1: Generate Authorization URL
```
https://auth.mercadopago.com/authorization
  ?client_id=APP_ID
  &response_type=code
  &platform_id=mp
  &state=RANDOM_STATE_TOKEN
  &redirect_uri=https://ourplatform.com/connect/mercadopago/callback
```

| Parameter | Description |
|-----------|-------------|
| `client_id` | Your application's APP_ID (from "Your integrations" dashboard) |
| `response_type` | Always `code` |
| `platform_id` | Always `mp` |
| `state` | Random unique string to prevent CSRF. Store server-side to validate on callback. |
| `redirect_uri` | Must match exactly what's configured in your MP application settings |

### Step 2: Merchant Authorizes
The merchant is redirected to MercadoPago, logs in, and authorizes your application. MP redirects back to your `redirect_uri` with:
```
https://ourplatform.com/connect/mercadopago/callback?code=TG-XXXXXXXX-241983636&state=RANDOM_STATE_TOKEN
```

### Step 3: Exchange Code for Access Token
```typescript
// IMPORTANT: The code expires in 10 minutes. Exchange immediately.
const response = await fetch('https://api.mercadopago.com/oauth/token', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    client_id: process.env.MP_CLIENT_ID,
    client_secret: process.env.MP_CLIENT_SECRET,
    code: authorizationCode,              // From callback query param
    grant_type: 'authorization_code',
    redirect_uri: process.env.MP_REDIRECT_URI,
    test_token: false                     // true for sandbox tokens
  })
});

const data = await response.json();
// data.access_token  -> valid for 180 days
// data.refresh_token -> use to get new access_token
// data.user_id       -> merchant's MP user ID
// data.public_key    -> merchant's public key
// data.token_type    -> "Bearer"
// data.expires_in    -> seconds until expiration
// data.scope         -> granted scopes
```

### Step 4: Refresh Token (Before Expiry)
```typescript
const response = await fetch('https://api.mercadopago.com/oauth/token', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    client_id: process.env.MP_CLIENT_ID,
    client_secret: process.env.MP_CLIENT_SECRET,
    grant_type: 'refresh_token',
    refresh_token: storedRefreshToken
  })
});
```

### Critical Notes
- **Authorization code expires in 10 minutes.** Exchange it immediately.
- **Access token expires in 180 days (6 months).** Set up a cron job to refresh before expiry.
- **For sandbox testing:** Send `test_token: true` when exchanging the code.
- **The `state` parameter is crucial** for CSRF protection. Generate a random string, store it in the session, and validate it on callback.

---

## 5. Marketplace Model (Fees & Commissions)

### How It Works
MercadoPago's marketplace model allows a platform (us) to:
1. Process payments on behalf of sellers (using their OAuth credentials)
2. Automatically collect a commission (`marketplace_fee`) on each transaction
3. The fee is deducted from the seller's payment and sent to the platform's MP account

### Setting Fees

#### With Checkout Pro (Preference)
```typescript
preference.create({
  body: {
    items: [{ title: 'Product', quantity: 1, unit_price: 1000 }],
    marketplace_fee: 100  // Platform takes ARS $100, seller gets $900
  }
});
```

#### With Checkout API (Payments)
```typescript
// Use `application_fee` instead of `marketplace_fee`
payment.create({
  body: {
    transaction_amount: 1000,
    application_fee: 100,  // Platform commission
    // ... other payment fields
  }
});
```

### Key Differences
| | Checkout Pro | Checkout API |
|---|---|---|
| Fee field | `marketplace_fee` | `application_fee` |
| Set on | Preference | Payment |
| Requires OAuth | Yes | Yes |

### Fee Considerations
- The fee is always in the local currency
- Maximum fee is limited by MercadoPago (varies by country)
- The fee is deducted from the seller's receivable, not added to the buyer's total
- MercadoPago's own processing fee is charged separately (to the seller)

---

## 6. Common Pitfalls and Gotchas

### Sandbox vs Production
- **Separate credentials:** Test (`public_key_test`, `access_token_test`) vs Production (`public_key`, `access_token`)
- **Test accounts:** Create test buyer/seller accounts from the MP developer dashboard. You cannot use real accounts in sandbox.
- **`sandbox_init_point` vs `init_point`:** In development, always use `sandbox_init_point`. The production `init_point` will fail with test credentials.
- **`test_token: true`:** When doing OAuth in sandbox, you must pass `test_token: true` when exchanging the authorization code.
- **Test card numbers:** MP provides specific test card numbers for each country. Real cards do not work in sandbox.

### Rate Limits
- MercadoPago does not publicly document strict rate limits, but in practice:
  - Preference creation: ~100 requests/second per access_token
  - Payment searches: lower limits, use webhooks instead of polling
  - If rate limited, you get HTTP 429. Implement exponential backoff.
- The Node SDK has built-in retry logic for 5xx errors (see `RestClient` source: retries on `status >= 500`).

### Country-Specific Differences
| Country | Currency | Notable Differences |
|---------|----------|-------------------|
| Argentina (MLA) | ARS | Rapipago, Pago Facil, Installments without Card |
| Brazil (MLB) | BRL | Pix, Boleto, most payment methods |
| Mexico (MLM) | MXN | OXXO, SPEI |
| Colombia (MCO) | COP | PSE, Efecty, Baloto |
| Chile (MLC) | CLP | Servipag, Webpay |
| Peru (MPE) | PEN | PagoEfectivo |
| Uruguay (MLU) | UYU | Abitab, RedPagos |

- **API base URL changes per country:**
  - `https://api.mercadopago.com` (universal, recommended)
- **Auth URL changes per country:**
  - Argentina: `https://auth.mercadopago.com.ar/authorization`
  - Brazil: `https://auth.mercadopago.com.br/authorization`

### Other Gotchas
- **`external_reference` is critical:** Always set it to your internal order ID. This is the only reliable way to correlate MP payments with your orders.
- **Preference expiration:** By default, preferences do not expire. Always set `expires: true` and `date_of_expiration` for chat-based links to prevent stale payments.
- **Duplicate webhooks:** MP may send the same notification multiple times. Always implement idempotency (check if you already processed a payment ID).
- **`binary_mode`:** When `true`, payments can only be `approved` or `rejected` (no `in_process`/`pending`). Useful for instant-result flows, but excludes cash payment methods.
- **Currency format:** Always use the numeric amount (e.g., `75.76`), never strings. The SDK types enforce this.
- **Webhook URL must be HTTPS** and publicly accessible. No localhost, no self-signed certs.

---

## 7. Webhook Security

### Signature Verification (HMAC-SHA256)

MercadoPago sends two headers with every webhook:
- `x-signature`: Contains `ts=<timestamp>,v1=<hmac_hash>`
- `x-request-id`: Unique request identifier

### Verification Algorithm
```typescript
import crypto from 'crypto';

function verifyWebhookSignature(
  xSignature: string,
  xRequestId: string,
  dataId: string,       // from query param `data.id`
  secret: string        // your webhook secret from MP dashboard
): boolean {
  // 1. Parse x-signature header
  const parts = xSignature.split(',');
  let ts = '';
  let hash = '';

  for (const part of parts) {
    const [key, value] = part.split('=').map(s => s.trim());
    if (key === 'ts') ts = value;
    if (key === 'v1') hash = value;
  }

  // 2. Build the manifest string
  const manifest = `id:${dataId};request-id:${xRequestId};ts:${ts};`;

  // 3. Calculate HMAC-SHA256
  const hmac = crypto.createHmac('sha256', secret);
  hmac.update(manifest);
  const calculatedHash = hmac.digest('hex');

  // 4. Compare (use timing-safe comparison in production)
  return crypto.timingSafeEqual(
    Buffer.from(calculatedHash),
    Buffer.from(hash)
  );
}
```

### Webhook Payload Format
```json
{
  "id": 12345,
  "live_mode": true,
  "type": "payment",
  "date_created": "2015-03-25T10:04:58.396-04:00",
  "user_id": 44444,
  "api_version": "v1",
  "action": "payment.created",
  "data": {
    "id": "999999999"
  }
}
```

### Webhook Topics for Our Use Case
| Topic | Events | Use |
|-------|--------|-----|
| `payment` | `payment.created`, `payment.updated` | **Primary** - Track payment status changes |
| `topic_merchant_order_wh` | Order created/closed/expired | Group multiple payments into one order |
| `topic_claims_integration_wh` | Refunds, claims | Handle disputes |
| `topic_chargebacks_wh` | Chargeback events | Handle chargebacks |
| `stop_delivery_op_wh` | Fraud alerts | Stop delivery if fraud detected |
| `mp-connect` | OAuth link/unlink | Track merchant connections |

### Idempotency & Retry Behavior
- **MP retries webhooks** if your endpoint does not return HTTP 200/201 within a reasonable timeout.
- **Always return 200 immediately** and process asynchronously. If your endpoint takes too long, MP will retry.
- **Store processed payment IDs** in a set/table. Before processing a webhook, check if `data.id` was already handled.
- **The `id` field in the payload** is the notification ID, not the payment ID. The payment ID is in `data.id`.
- **After receiving a webhook**, always fetch the full payment details via the API to get the current status (don't rely solely on webhook data).

### Webhook Configuration
Two methods:
1. **Via "Your integrations" dashboard** - Configure a global webhook URL and select event topics
2. **Per-preference `notification_url`** - Set on each preference creation. Add `?source_news=webhooks` to receive only webhook notifications (not legacy IPN).

---

## 8. Payment Status Flow

### Status Lifecycle
```
                    +---> approved ---> [DONE: Money released to seller]
                    |
created ---> pending/in_process --+--> rejected ---> [DONE: No charge]
                    |             |
                    |             +--> cancelled ---> [DONE: Cancelled by buyer/seller]
                    |
                    +---> authorized ---> captured ---> approved
                                    (only for auth+capture flow)
```

### Payment Statuses

| Status | Description | What to do |
|--------|-------------|-----------|
| `pending` | Payment initiated but not completed (e.g., buyer chose cash payment, awaiting deposit) | Show "payment pending" to customer. Wait for webhook update. |
| `approved` | Payment confirmed and money is being processed | Confirm order. Notify customer. Deliver product/service. |
| `authorized` | Payment authorized but not yet captured (pre-auth flow) | Capture within allowed window. |
| `in_process` | Payment is being reviewed (anti-fraud, manual review) | Wait. Do not deliver yet. |
| `rejected` | Payment was declined (insufficient funds, invalid card, etc.) | Notify customer. Offer to retry. |
| `cancelled` | Payment was cancelled | Mark order as cancelled. |
| `refunded` | Payment was refunded (full) | Update order status. |
| `charged_back` | Customer disputed the charge with their bank | Handle dispute process. |

### Status Detail (Common Rejection Reasons)
| `status_detail` | Meaning |
|-----------------|---------|
| `cc_rejected_insufficient_amount` | Insufficient funds |
| `cc_rejected_bad_filled_card_number` | Wrong card number |
| `cc_rejected_bad_filled_date` | Wrong expiry date |
| `cc_rejected_bad_filled_security_code` | Wrong CVV |
| `cc_rejected_bad_filled_other` | Other card error |
| `cc_rejected_call_for_authorize` | Card requires phone authorization |
| `cc_rejected_duplicated_payment` | Duplicate payment detected |
| `cc_rejected_high_risk` | Rejected by anti-fraud |
| `cc_rejected_max_attempts` | Too many retries |
| `cc_rejected_blacklist` | Card is blacklisted |
| `accredited` | Payment approved |
| `pending_contingency` | MP is processing |
| `pending_review_manual` | Under manual review |
| `pending_waiting_payment` | Waiting for cash payment (Rapipago, etc.) |

### Fetching Full Payment Details After Webhook
```typescript
import { MercadoPagoConfig, Payment } from 'mercadopago';

const client = new MercadoPagoConfig({
  accessToken: merchantAccessToken,
  options: { timeout: 5000 }
});

const payment = new Payment(client);
const paymentData = await payment.get({ id: paymentId });

// paymentData.status          -> 'approved', 'pending', 'rejected', etc.
// paymentData.status_detail   -> 'accredited', 'cc_rejected_...', etc.
// paymentData.external_reference -> your order ID
// paymentData.transaction_amount -> amount paid
// paymentData.currency_id     -> 'ARS', 'BRL', etc.
// paymentData.payment_method_id -> 'visa', 'master', 'rapipago', etc.
// paymentData.payer.email     -> buyer's email
```

---

## 9. Recommended Architecture for Seller-Agent

```
+------------------+     +-------------------+     +-------------------+
| WhatsApp/IG Bot  |---->| Seller-Agent API  |---->| MercadoPago API   |
| (Meta Cloud API) |     | (Next.js Server)  |     | (Preferences)     |
+------------------+     +-------------------+     +-------------------+
        |                         |                         |
        |                   +-----v-----+                   |
        |                   | PostgreSQL |                   |
        |                   | - merchants|                   |
        |                   | - orders   |                   |
        |                   | - payments |                   |
        |                   | - mp_conns |                   |
        |                   +-----------+                   |
        |                         ^                         |
        |                         |                         |
        +-- Confirmation -------- | <---- Webhook ----------+
            Message               |       (payment.updated)
```

### Key Implementation Points
1. **Use Checkout Pro** - Create preferences, send `init_point` URLs via chat
2. **OAuth for merchant onboarding** - Each merchant connects their MP account once
3. **`marketplace_fee`** - Collect platform commission on every transaction
4. **Webhook-driven** - All payment status updates come via webhooks; never poll
5. **`external_reference`** - Always set to `{merchantId}:{orderId}` for traceability
6. **Token refresh cron** - Refresh OAuth tokens before 180-day expiry
7. **Idempotent webhook handler** - Deduplicate by payment ID
8. **HMAC verification** - Verify every webhook signature

### Node SDK Package
```bash
npm install mercadopago
# Current version: 2.12.0 (TypeScript-native, class-based API)
```

---

## 10. References

- [Checkout Pro Docs](https://www.mercadopago.com.ar/developers/en/docs/checkout-pro/overview)
- [Checkout Bricks Docs](https://www.mercadopago.com.ar/developers/en/docs/checkout-bricks/overview)
- [Checkout API Docs](https://www.mercadopago.com.ar/developers/en/docs/checkout-api-orders/overview)
- [Webhooks Docs](https://www.mercadopago.com.ar/developers/en/docs/your-integrations/notifications/webhooks)
- [OAuth / Credentials](https://www.mercadopago.com.ar/developers/en/docs/your-integrations/credentials)
- [Node SDK (GitHub)](https://github.com/mercadopago/sdk-nodejs)
- [API Reference](https://www.mercadopago.com.ar/developers/en/reference)
- [MP Developer Dashboard](https://www.mercadopago.com.ar/developers/panel/app)
