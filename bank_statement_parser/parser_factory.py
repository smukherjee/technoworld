from typing import Type
from .base_parser import BankStatementParser
from .icici_parser_new import ICICIParser
from .icici_parser_camelot import ICICIParserCamelot

def get_bank_parser(bank_type: str) -> Type[BankStatementParser]:
    """Factory function to get the appropriate bank parser"""
    parsers = {
        'ICICI': ICICIParser,
        'ICICI_CAMELOT': ICICIParserCamelot,
        # Add more banks here as they are implemented
    }
    
    parser_class = parsers.get(bank_type.upper())
    if not parser_class:
        raise ValueError(f"Unsupported bank type: {bank_type}")
    
    return parser_class
