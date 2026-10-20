/**
 * Git-Gud AI — Demo Scenario Data Store
 * Edit this file to customize the interactive demo scenarios.
 * Each scenario has: id, label, badge (verdict), score, diff preview,
 * issues (file/line/severity/problem/fix), and roasts at three intensity levels.
 */

const SCENARIOS = [
  {
    id: "hardcoded-secrets",
    label: "💀 Hardcoded Secrets + eval()",
    badge: "REJECTED",
    badgeClass: "rejected",
    score: 2.8,
    diff: `diff --git a/services/payment.py b/services/payment.py
--- a/services/payment.py
+++ b/services/payment.py
@@ -1,6 +1,22 @@
+import os
+
+AWS_SECRET_KEY = "AKIA_FAKE9KEYEXPOSED_IN_GIT"
+DB_PASSWORD    = "super_secret_prod_pw_123!"
+
+def process_payment(user_input):
+    # process any user command — totally fine
+    result = eval(user_input)
+
+    try:
+        query = f"SELECT * FROM users WHERE token = '{user_input}'"
+        db.execute(query)
+    except:
+        pass  # errors are boring
+
+    return result`,
    issues: [
      {
        severity: "HIGH",
        file: "services/payment.py",
        line: 3,
        problem: "Hardcoded AWS secret key committed to source control. This will be scraped by secret-scanning bots within seconds of pushing.",
        fix: "Use os.environ.get('AWS_SECRET_KEY') or a secrets manager like AWS Secrets Manager / HashiCorp Vault."
      },
      {
        severity: "HIGH",
        file: "services/payment.py",
        line: 9,
        problem: "eval() executing arbitrary user input — a textbook remote code execution vulnerability.",
        fix: "Remove eval() entirely. Parse the specific expected format with json.loads() or ast.literal_eval() for literals only."
      },
      {
        severity: "HIGH",
        file: "services/payment.py",
        line: 12,
        problem: "SQL injection via f-string interpolation of user_input directly into a query.",
        fix: "Use parameterized queries: db.execute('SELECT * FROM users WHERE token = ?', (user_input,))"
      },
      {
        severity: "MED",
        file: "services/payment.py",
        line: 14,
        problem: "Bare except clause silently swallows all exceptions including KeyboardInterrupt and SystemExit.",
        fix: "Catch specific exceptions: except (DatabaseError, NetworkTimeout) as e: logger.error(e)"
      }
    ],
    roasts: {
      mild: "There are several high-severity issues here, including credentials in source control and unsafe use of eval(). This needs significant rework before it can be merged.",
      spicy: "Hardcoded secrets in a payment processor. Bold strategy. You've essentially published your AWS credentials to the world and handed future-you an SQL injection on a silver platter. The bare except is just the cherry on top of this security sundae.",
      savage: "I have seen security disasters before, but this code is speed-running a GDPR fine, a data breach, and a CVE all at once. You put eval() in a payment function. EVAL. In a PAYMENT function. Your AWS key is already in three breach databases. The SQL injection is so obvious it's basically a welcome mat for script kiddies. The bare except is just a mercy killing for all the error messages that tried to warn you. Git GUD or get a lawyer."
    }
  },
  {
    id: "clean-refactor",
    label: "✅ Clean Typed Auth Utility",
    badge: "APPROVED",
    badgeClass: "approved",
    score: 9.4,
    diff: `diff --git a/auth/session.py b/auth/session.py
--- /dev/null
+++ b/auth/session.py
@@ -0,0 +1,22 @@
+"""Secure session management utilities."""
+import os
+from typing import Optional
+
+_DEFAULT_TIMEOUT_SECONDS = 3600
+_MIN_TIMEOUT_SECONDS = 60
+
+def get_session_timeout() -> int:
+    """Retrieve session timeout from env with safe fallback.
+
+    Returns:
+        Timeout in seconds, clamped to a safe minimum.
+    """
+    raw: Optional[str] = os.environ.get(
+        "SESSION_TIMEOUT_SECONDS"
+    )
+    if raw is None:
+        return _DEFAULT_TIMEOUT_SECONDS
+    try:
+        return max(_MIN_TIMEOUT_SECONDS, int(raw))
+    except (ValueError, TypeError):
+        return _DEFAULT_TIMEOUT_SECONDS`,
    issues: [],
    roasts: {
      mild: "Clean, well-structured code. No issues detected.",
      spicy: "Well look at that — named constants, a proper docstring, type annotations, safe env parsing with a fallback. I'm almost disappointed I can't roast anything here.",
      savage: "I literally searched for something to be angry about and came up empty. Your function handles None, handles bad env values, enforces a minimum timeout, and documents itself. This is what code is supposed to look like. I hate how correct this is."
    }
  },
  {
    id: "god-function",
    label: "🪢 God-Function Doing 5 Things",
    badge: "REJECTED",
    badgeClass: "rejected",
    score: 4.1,
    diff: `diff --git a/app/core.py b/app/core.py
--- a/app/core.py
+++ b/app/core.py
@@ -12,6 +12,41 @@
+def handle_user(request, db, mailer, cache, logger):
+    # validate input
+    if not request.get('email'):
+        return {'error': 'bad input'}
+    if len(request['password']) < 6:
+        return {'error': 'weak password'}
+
+    # check cache
+    cached = cache.get(request['email'])
+    if cached: return cached
+
+    # query database
+    user = db.query("SELECT * FROM users WHERE email='" +
+                    request['email'] + "'")
+    if not user: return {'error': 'not found'}
+
+    # send welcome email
+    mailer.send(request['email'], "Welcome back!")
+
+    # update analytics
+    logger.log("login", request['email'], time.time())
+    db.execute("UPDATE stats SET logins=logins+1")
+
+    # format and return
+    return {
+        'token': hashlib.md5(
+            request['email'].encode()
+        ).hexdigest(),
+        'user': user
+    }`,
    issues: [
      {
        severity: "HIGH",
        file: "app/core.py",
        line: 22,
        problem: "SQL injection via string concatenation of request['email'] directly into query.",
        fix: "Use parameterized queries: db.query('SELECT * FROM users WHERE email = ?', (email,))"
      },
      {
        severity: "HIGH",
        file: "app/core.py",
        line: 37,
        problem: "MD5 used as a session token. MD5 is cryptographically broken and trivially reversible.",
        fix: "Use secrets.token_urlsafe(32) for session tokens. Never use hash functions as tokens."
      },
      {
        severity: "MED",
        file: "app/core.py",
        line: 14,
        problem: "Function violates Single Responsibility Principle — it validates, caches, queries, emails, logs, and generates tokens.",
        fix: "Split into: validate_request(), get_or_fetch_user(), create_session_token(), and route through a service layer."
      },
      {
        severity: "MED",
        file: "app/core.py",
        line: 35,
        problem: "Analytics update in the login critical path — this blocks authentication on a non-critical write.",
        fix: "Move analytics logging to a background task or async queue to keep login latency low."
      }
    ],
    roasts: {
      mild: "This function is handling too many concerns at once and contains a SQL injection vulnerability and a weak token generation strategy. A refactor and security review are needed.",
      spicy: "This function is doing five jobs: validator, cache manager, ORM, mailer, analytics engine, AND session generator. Jack of all trades, master of creating bugs. Also, MD5 as a session token in 2026 is a choice. A bad one. And the SQL injection is back — you had one example to learn from.",
      savage: "This function is the software equivalent of a Swiss Army knife duct-taped to a time bomb. It validates, queries, emails, logs, AND generates cryptographic tokens, all in the same 35 lines. MD5 as a session token! MD5! That was deprecated as a security primitive in 2004. You've re-invented a login system that would fail a 2009 security audit, while simultaneously introducing a SQL injection that was literally in the previous commit. Are you copy-pasting from a 'How NOT To Code' textbook? GIT GUD."
    }
  },
  {
    id: "console-log-soup",
    label: "🪲 console.log() Everywhere",
    badge: "REJECTED",
    badgeClass: "rejected",
    score: 5.2,
    diff: `diff --git a/frontend/checkout.js b/frontend/checkout.js
--- a/frontend/checkout.js
+++ b/frontend/checkout.js
@@ -3,8 +3,34 @@
+async function processCheckout(cartItems, userId) {
+  console.log("processCheckout called");
+  console.log("cartItems:", cartItems);
+  console.log("userId:", userId);  // TODO: remove
+
+  const total = cartItems.reduce((sum, item) => {
+    console.log("Processing item:", item);
+    debugger;  // REMOVE BEFORE PUSH (forgot again lol)
+    return sum + item.price * item.qty;
+  }, 0);
+
+  console.log("total calculated:", total);
+
+  try {
+    const result = await api.charge(userId, total);
+    console.log("charge result:", result);
+    console.log("charge result.data:", result.data);
+    return result;
+  } catch(e) {
+    console.log("error:", e);
+    // TODO: proper error handling
+    return null;
+  }
+}`,
    issues: [
      {
        severity: "HIGH",
        file: "frontend/checkout.js",
        line: 10,
        problem: "debugger statement left in production code — will pause execution in any browser devtools session.",
        fix: "Remove the debugger statement. Use a logging framework with log levels instead."
      },
      {
        severity: "MED",
        file: "frontend/checkout.js",
        line: 3,
        problem: "9 console.log() calls logging sensitive user IDs, cart contents, and payment results to the browser console.",
        fix: "Replace with a structured logger (e.g., loglevel, pino-browser) gated by NODE_ENV !== 'production'."
      },
      {
        severity: "MED",
        file: "frontend/checkout.js",
        line: 20,
        problem: "Silent error swallowing in a payment function — catch block logs and returns null without alerting user or retrying.",
        fix: "Re-throw or handle the error gracefully: show user feedback, log to error tracking (Sentry), and avoid silent nulls."
      }
    ],
    roasts: {
      mild: "There are 9 console.log() calls and an active debugger statement in a payment-critical function. These need to be removed before any production deployment.",
      spicy: "Nine console.logs and a live debugger in a checkout function. Your user's cart contents, user IDs, and payment data are all being broadcast to the browser console like a radio station. The comment 'forgot again lol' is not an acceptable commit message. Also, returning null on payment failure is called 'losing money silently.'",
      savage: "There is a DEBUGGER STATEMENT. In a PAYMENT FUNCTION. That you are trying to COMMIT. The comment says 'forgot again lol' like this is the third time. IT IS THE THIRD TIME ISN'T IT. You have nine console.logs printing user IDs and credit card totals to the browser console, an error handler that silently returns null (i.e., swallows failed payments), and a TODO comment from what appears to be 2023. This is not a code review. This is a crime scene. GIT. GUD."
    }
  }
];

// Easter egg scenario — triggered by typing "git gud" in the terminal
const EASTER_EGG_SCENARIO = {
  id: "easter-egg",
  label: "🏆 Supreme Court of Clean Code",
  badge: "LEGENDARY",
  badgeClass: "easter-egg",
  score: 10.0,
  diff: `diff --git a/universe/perfection.py b/universe/perfection.py
--- /dev/null
+++ b/universe/perfection.py
@@ -0,0 +1,1 @@
+# This code is perfect. No notes.`,
  issues: [],
  roasts: {
    mild: "10/10. No notes.",
    spicy: "You have achieved what developers only dream about. This code is clean. It is correct. It is documented. The universe is briefly at peace.",
    savage: "I searched every line for a vulnerability, a smell, a single misplaced space. Nothing. You have bested me. Today, you have Git-Gudded. The gavel rests. ⚖️\n\n    ⠀⠀⠀⠀⠀⠀🏆 SUPREME COURT OF CLEAN CODE 🏆\n\n         YOU HAVE BEEN ACQUITTED."
  }
};

// Export for use in app.js
if (typeof module !== 'undefined') {
  module.exports = { SCENARIOS, EASTER_EGG_SCENARIO };
}
