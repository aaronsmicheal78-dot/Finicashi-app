# # from decimal import Decimal
# # from datetime import datetime
# # def test_withdrawal_debug():
# #     from app import create_app
# #     app = create_app()
# #     with app.app_context():
# #         from blueprints.withdraw_helpers import WithdrawalValidator, WithdrawalProcessor
        
# #         print("\n=== TESTING WITH DEBUG VALIDATION ===")
        
# #         # Test just the validator
# #         success, message, user = WithdrawalValidator.validate_withdrawal(
# #             user_id=18,
# #             amount=Decimal('5000'),
# #             phone='0741256873'
# #         )
        
# #         print(f"\nValidator result: {success}")
# #         print(f"Message: {message}")
        
# #         if success:
# #             # Test full processor
# #             print("\n--- Testing full processor ---")
# #             success2, message2, details2 = WithdrawalProcessor.process_withdrawal_request(
# #                 user_id=18,
# #                 amount=Decimal('5000'),
# #                 phone='0741256873',
# #                 idempotency_key=f"TEST-{int(datetime.now().timestamp())}"
# #             )
# #             print(f"Processor result: {success2}")
# #             print(f"Message: {message2}")

# # test_withdrawal_debug()

# def test_phone_comparison():
#     phone = '256741256873'
#     user_phone = '0741256873'
    
#     print(f"phone: {phone}")
#     print(f"user_phone: {user_phone}")
#     print(f"phone.replace('256', '0'): {phone.replace('256', '0')}")
#     print(f"phone.replace('256', '0', 1): {phone.replace('256', '0', 1)}")
    
#     # Test comparisons
#     print(f"\nComparison results:")
#     print(f"  user_phone == phone: {user_phone == phone}")
#     print(f"  user_phone == phone.replace('256', '0'): {user_phone == phone.replace('256', '0')}")
#     print(f"  user_phone == phone.replace('256', '0', 1): {user_phone == phone.replace('256', '0', 1)}")
    
#     # Check types and lengths
#     print(f"\nLengths:")
#     print(f"  len(user_phone): {len(user_phone)}")
#     print(f"  len(phone.replace('256', '0')): {len(phone.replace('256', '0'))}")
#     print(f"  len(phone.replace('256', '0', 1)): {len(phone.replace('256', '0', 1))}")
    
#     # Check actual characters
#     print(f"\nCharacter by character:")
#     replaced = phone.replace('256', '0', 1)
#     for i in range(min(len(user_phone), len(replaced))):
#         if user_phone[i] != replaced[i]:
#             print(f"  Position {i}: '{user_phone[i]}' vs '{replaced[i]}'")
    
#     # This should work - use regex to replace ONLY the first occurrence
#     import re
#     phone_fixed = re.sub(r'^256', '0', phone)
#     print(f"\nUsing regex replace: {phone_fixed}")
#     print(f"Matches user_phone: {user_phone == phone_fixed}")

# test_phone_comparison()
from datetime import datetime
def test_user_18_withdrawal_after_fix():
    from app import create_app
    app = create_app()
    with app.app_context():
        from blueprints.withdraw_helpers import WithdrawalValidator, WithdrawalProcessor
        
        print("\n" + "="*60)
        print("TESTING USER 18 WITHDRAWAL AFTER FIX")
        print("="*60)
        
        # Test validation
        success, message, user = WithdrawalValidator.validate_withdrawal(
            user_id=18,
            amount=5000,
            phone='0741256873'
        )
        
        print(f"\nValidation Result: {success}")
        print(f"Message: {message}")
        
        if success:
            # Test full withdrawal
            success2, message2, details2 = WithdrawalProcessor.process_withdrawal_request(
                user_id=18,
                amount=5000,
                phone='0741256873',
                idempotency_key=f"TEST-FIX-{int(datetime.now().timestamp())}"
            )
            
            print(f"\nWithdrawal Result: {success2}")
            print(f"Message: {message2}")
            if details2:
                print(f"Details: {details2}")
                
            if success2:
                print("\n✅ USER 18 CAN NOW WITHDRAW!")
            else:
                print(f"\n❌ Still failing: {message2}")
        else:
            print(f"\n❌ Validation failed: {message}")

test_user_18_withdrawal_after_fix()