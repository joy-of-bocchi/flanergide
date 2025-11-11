package com.flanergide.data

/**
 * SensitiveDataRedactor - Regex-based redaction of sensitive patterns.
 *
 * Applies client-side redaction to remove passwords, credit cards, API keys,
 * and other sensitive data before storage.
 */
object SensitiveDataRedactor {
    private val patterns = listOf(
        // Passwords in common forms
        "password\\s*[=:]\\s*[\"']?[^\"'\\s]+[\"']?" to "password=[REDACTED]",
        "pass\\s*[=:]\\s*[\"']?[^\"'\\s]+[\"']?" to "pass=[REDACTED]",
        "pwd\\s*[=:]\\s*[\"']?[^\"'\\s]+[\"']?" to "pwd=[REDACTED]",

        // Credit cards (16 digits with optional separators)
        "\\b\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}\\b" to "[CREDIT_CARD]",

        // API keys, tokens, secrets
        "(?:api[_-]?key|token|auth|secret|bearer)\\s*[=:]\\s*[\"']?[^\"'\\s]+[\"']?" to "[TOKEN_REDACTED]",

        // Phone numbers (various formats)
        "\\b\\d{3}[-.]?\\d{3}[-.]?\\d{4}\\b" to "[PHONE]",
        "\\b\\(\\d{3}\\)\\s*\\d{3}[-.]?\\d{4}\\b" to "[PHONE]",

        // Email addresses
        "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b" to "[EMAIL]",

        // Social security numbers
        "\\b\\d{3}-\\d{2}-\\d{4}\\b" to "[SSN]",

        // URLs with credentials
        "https?://[^:]+:[^@]+@" to "https://[REDACTED_CREDS]@"
    )

    /**
     * Apply redaction to text using all defined patterns.
     */
    fun redact(text: String): String {
        var result = text
        patterns.forEach { (pattern, replacement) ->
            result = result.replace(Regex(pattern, RegexOption.IGNORE_CASE), replacement)
        }
        return result
    }

    /**
     * Apply context-aware redaction based on app package.
     */
    fun redactForApp(text: String, appPackage: String): String {
        return when {
            // Banking/payment apps - aggressive redaction
            appPackage.contains("banking", ignoreCase = true) ||
            appPackage.contains("paypal", ignoreCase = true) ||
            appPackage.contains("venmo", ignoreCase = true) -> {
                redactFinancial(text)
            }

            // Password managers - don't log at all
            appPackage.contains("password", ignoreCase = true) ||
            appPackage.contains("1password", ignoreCase = true) ||
            appPackage.contains("lastpass", ignoreCase = true) ||
            appPackage.contains("bitwarden", ignoreCase = true) -> {
                "[PASSWORD_MANAGER_ACTIVITY]"
            }

            // Email apps - redact emails but keep subjects
            appPackage.contains("gmail", ignoreCase = true) ||
            appPackage.contains("mail", ignoreCase = true) -> {
                redactEmails(text)
            }

            // Default: standard redaction
            else -> redact(text)
        }
    }

    private fun redactFinancial(text: String): String {
        var result = redact(text)
        // Also redact dollar amounts and numbers
        result = result.replace(Regex("\\$?\\d+([.,]\\d{2})?"), "[AMOUNT]")
        return result
    }

    private fun redactEmails(text: String): String {
        // Keep structure but redact email addresses
        return redact(text)
    }
}
