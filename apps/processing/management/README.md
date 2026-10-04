# Azure connection diagnostic

From the repository root, run:

```bash
.venv/bin/python manage.py check_azure
```

This makes a read-only resource-info request using the same configuration as
extraction. It uploads no invoice and exits unsuccessfully for authentication,
configuration, or connection errors. HTTP 200 confirms authentication, not that
a particular invoice can be extracted.

For HTTP 401:

1. Check the resource's subscription status in Azure Portal. A disabled
   subscription must be reactivated before retrying; changing keys does not
   reactivate it.
2. Copy the endpoint and key from **Keys and Endpoint** on the same Document
   Intelligence resource into the ignored `.env` file.
3. Check for environment variables overriding `.env`, then fully restart Django.
   Settings are loaded at startup; existing environment variables take precedence.
4. Run the diagnostic again. After HTTP 200, use **Retry extraction** on the saved
   failed document. Review the extracted invoice before exporting it.

HTTP failures retain status, validated error code and request ID when available.
Provider error messages and bodies are omitted to avoid exposing sensitive data.
Successful responses continue to use the existing raw-response storage.

Subscription recovery guidance:
https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/subscription-disabled
