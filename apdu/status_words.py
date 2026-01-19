"""
Status Words (SW1 SW2) used in smart card / USIM APDU responses.

A card response is generally in the format as :
    <optional response data> + SW1 + SW2

"""

# Success
SW_SUCCESS = b"\x90\x00"

# Generic errors / protocol
SW_WRONG_LENGTH = b"\x67\x00"          
SW_INS_NOT_SUPPORTED = b"\x6D\x00"     
SW_CLA_NOT_SUPPORTED = b"\x6E\x00"     
# File system / selection related
SW_FILE_NOT_FOUND = b"\x6A\x82"        
SW_RECORD_NOT_FOUND = b"\x6A\x83"      
SW_WRONG_P1P2 = b"\x6B\x00"            
SW_FUNC_NOT_SUPPORTED = b"\x6A\x81"    
SW_COMMAND_NOT_ALLOWED = b"\x69\x86"   
SW_COND_NOT_SATISFIED = b"\x69\x85"   

# Security
SW_SECURITY_STATUS_NOT_SATISFIED = b"\x69\x82" 

# Convenience: mapping for debugging/logging
SW_NAMES = {
    SW_SUCCESS: "9000 Success",
    SW_WRONG_LENGTH: "6700 Wrong length",
    SW_INS_NOT_SUPPORTED: "6D00 INS not supported",
    SW_CLA_NOT_SUPPORTED: "6E00 CLA not supported",
    SW_FILE_NOT_FOUND: "6A82 File not found",
    SW_RECORD_NOT_FOUND: "6A83 Record not found",
    SW_WRONG_P1P2: "6B00 Wrong P1/P2",
    SW_FUNC_NOT_SUPPORTED: "6A81 Function not supported",
    SW_COMMAND_NOT_ALLOWED: "6986 Command not allowed",
    SW_COND_NOT_SATISFIED: "6985 Conditions not satisfied",
    SW_SECURITY_STATUS_NOT_SATISFIED: "6982 Security status not satisfied",
}
