-- Disable Flooss payment provider
UPDATE payment_provider
   SET flooss_account_email = NULL,
       flooss_client_id = NULL,
       flooss_client_secret = NULL
 WHERE code = 'flooss';
