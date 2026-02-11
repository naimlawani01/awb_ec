"""AWB XML Parser - Extracts detailed information from document_data field."""
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class AWBItem:
    """Single rate/charge line item."""
    pieces: int = 0
    gross_weight: float = 0.0
    chargeable_weight: float = 0.0
    rate_charge: float = 0.0
    total: float = 0.0
    nature: str = ""
    scale: str = "K"
    rate_class: str = ""
    item_number: str = ""
    dimensions: str = ""


@dataclass
class OtherCharge:
    """Other charges (PS, AWC, etc.)."""
    code: str = ""
    amount: float = 0.0
    due: str = ""  # "due agent" or "due carrier"
    three_letter_code: str = ""


@dataclass
class RouteInfo:
    """Flight routing information."""
    to: List[str] = None
    by: List[str] = None
    flights: List[str] = None
    
    def __post_init__(self):
        self.to = self.to or []
        self.by = self.by or []
        self.flights = self.flights or []


@dataclass 
class ChargesSummary:
    """Summary of all charges."""
    weight_charge_prepaid: float = 0.0
    weight_charge_collect: float = 0.0
    valuation_charge_prepaid: float = 0.0
    valuation_charge_collect: float = 0.0
    tax_prepaid: float = 0.0
    tax_collect: float = 0.0
    other_due_agent_prepaid: float = 0.0
    other_due_agent_collect: float = 0.0
    other_due_carrier_prepaid: float = 0.0
    other_due_carrier_collect: float = 0.0
    total_prepaid: float = 0.0
    total_collect: float = 0.0


@dataclass
class AWBDetails:
    """Complete AWB document details parsed from XML."""
    # Basic info
    awb_type: str = ""
    airline_prefix: str = ""
    serial_number: str = ""
    hawb: str = ""
    
    # Payment
    weight_payment_type: str = ""
    other_charges_payment_type: str = ""
    calculations: str = ""
    
    # Parties
    shipper_details: str = ""
    shipper_account: str = ""
    consignee_details: str = ""
    consignee_account: str = ""
    agent_details: str = ""
    agent_iata_code: str = ""
    issued_by_details: str = ""
    
    # Routing
    airport_departure: str = ""
    airport_departure_code: str = ""
    airport_destination: str = ""
    route: RouteInfo = None
    
    # Items/Rates
    items: List[AWBItem] = None
    total_pieces: int = 0
    total_weight: float = 0.0
    weight_scale: str = "K"
    items_total: float = 0.0
    
    # Other charges
    other_charges: List[OtherCharge] = None
    
    # Charges summary
    charges_summary: ChargesSummary = None
    
    # Currency & values
    currency: str = ""
    insurance: str = ""
    value_carrier: str = ""
    value_customs: str = ""
    
    # Additional info
    reference_number: str = ""
    handling_information: str = ""
    accounting_information: str = ""
    sci: str = ""
    
    # Signatures
    shipper_signature: str = ""
    carrier_signature: str = ""
    carrier_date: str = ""
    carrier_place: str = ""
    
    # Notes
    notes: str = ""
    
    def __post_init__(self):
        self.items = self.items or []
        self.other_charges = self.other_charges or []
        self.route = self.route or RouteInfo()
        self.charges_summary = self.charges_summary or ChargesSummary()


class AWBParser:
    """Parser for AWB XML data stored in document_data field."""
    
    @staticmethod
    def parse(xml_data: bytes) -> Optional[AWBDetails]:
        """Parse AWB XML data and return structured AWBDetails."""
        if not xml_data:
            return None
            
        try:
            xml_string = xml_data.decode('utf-8')
            root = ET.fromstring(xml_string)
            
            details = AWBDetails()
            
            # Basic info
            details.awb_type = AWBParser._get_text(root, 'awb-type')
            details.airline_prefix = AWBParser._get_text(root, 'airline-prefix')
            details.serial_number = AWBParser._get_text(root, 'awb-serial-number')
            details.hawb = AWBParser._get_text(root, 'hawb')
            
            # Payment
            details.weight_payment_type = AWBParser._get_text(root, 'weight-payment-type')
            details.other_charges_payment_type = AWBParser._get_text(root, 'other-charges-payment-type')
            details.calculations = AWBParser._get_text(root, 'calculations')
            
            # Parties
            details.shipper_details = AWBParser._get_text(root, 'shipper-details')
            details.shipper_account = AWBParser._get_text(root, 'shipper-account-number')
            details.consignee_details = AWBParser._get_text(root, 'consignee-details')
            details.consignee_account = AWBParser._get_text(root, 'consignee-account-number')
            details.agent_details = AWBParser._get_text(root, 'agent-details')
            details.agent_iata_code = AWBParser._get_text(root, 'agent-iata-cargo-numeric-code')
            details.issued_by_details = AWBParser._get_text(root, 'issued-by-details')
            
            # Routing
            details.airport_departure = AWBParser._get_text(root, 'airport-departure')
            details.airport_departure_code = AWBParser._get_text(root, 'airport-city-code-departure')
            details.airport_destination = AWBParser._get_text(root, 'airport-destination')
            
            # Route info
            route = RouteInfo()
            route_to = root.find('route-to')
            if route_to is not None:
                route.to = [s.text for s in route_to.findall('string') if s.text]
            route_by = root.find('route-by')
            if route_by is not None:
                route.by = [s.text for s in route_by.findall('string') if s.text]
            flights = root.find('requested-flight')
            if flights is not None:
                route.flights = [s.text for s in flights.findall('string') if s.text]
            details.route = route
            
            # Parse items (rate description lines)
            details.items = AWBParser._parse_items(root)
            details.total_pieces = AWBParser._get_int(root, 'item-pieces')
            details.total_weight = AWBParser._get_float(root, 'item-weight')
            details.weight_scale = AWBParser._get_text(root, 'item-weight-scale') or 'K'
            details.items_total = AWBParser._get_float(root, 'item-total')
            
            # Parse other charges
            details.other_charges = AWBParser._parse_other_charges(root)
            
            # Parse charges summary
            details.charges_summary = AWBParser._parse_charges_summary(root)
            
            # Currency & values
            details.currency = AWBParser._get_text(root, 'currency')
            details.insurance = AWBParser._get_text(root, 'insurance')
            details.value_carrier = AWBParser._get_text(root, 'value-carrier')
            details.value_customs = AWBParser._get_text(root, 'value-customs')
            
            # Additional info
            details.reference_number = AWBParser._get_text(root, 'reference-number')
            details.handling_information = AWBParser._get_text(root, 'handling-information')
            details.accounting_information = AWBParser._get_text(root, 'accounting-information')
            details.sci = AWBParser._get_text(root, 'sci')
            
            # Signatures
            details.shipper_signature = AWBParser._get_text(root, 'shipper-signature')
            details.carrier_signature = AWBParser._get_text(root, 'carrier-signature')
            details.carrier_date = AWBParser._get_text(root, 'carrier-date')
            details.carrier_place = AWBParser._get_text(root, 'carrier-place')
            
            # Notes
            details.notes = AWBParser._get_text(root, 'notes')
            
            return details
            
        except Exception as e:
            print(f"Error parsing AWB XML: {e}")
            return None
    
    @staticmethod
    def _get_text(root: ET.Element, tag: str) -> str:
        """Get text content of a tag."""
        elem = root.find(tag)
        if elem is not None and elem.text:
            return elem.text.strip()
        return ""
    
    @staticmethod
    def _get_int(root: ET.Element, tag: str) -> int:
        """Get integer value of a tag."""
        text = AWBParser._get_text(root, tag)
        try:
            return int(text) if text else 0
        except ValueError:
            return 0
    
    @staticmethod
    def _get_float(root: ET.Element, tag: str) -> float:
        """Get float value of a tag."""
        text = AWBParser._get_text(root, tag)
        try:
            return float(text) if text else 0.0
        except ValueError:
            return 0.0
    
    @staticmethod
    def _parse_items(root: ET.Element) -> List[AWBItem]:
        """Parse awb-item elements."""
        items = []
        items_elem = root.find('items')
        if items_elem is not None:
            for item_elem in items_elem.findall('awb-item'):
                item = AWBItem(
                    pieces=AWBParser._get_int(item_elem, 'pieces'),
                    gross_weight=AWBParser._get_float(item_elem, 'gross-weight'),
                    chargeable_weight=AWBParser._get_float(item_elem, 'chargeable-weight'),
                    rate_charge=AWBParser._get_float(item_elem, 'rate-charge'),
                    total=AWBParser._get_float(item_elem, 'total'),
                    nature=AWBParser._get_text(item_elem, 'nature'),
                    scale=AWBParser._get_text(item_elem, 'scale') or 'K',
                    rate_class=AWBParser._get_text(item_elem, 'rate-class'),
                    item_number=AWBParser._get_text(item_elem, 'item-number'),
                    dimensions=AWBParser._get_text(item_elem, 'dimensions'),
                )
                items.append(item)
        return items
    
    @staticmethod
    def _parse_other_charges(root: ET.Element) -> List[OtherCharge]:
        """Parse other-charges elements."""
        charges = []
        charges_elem = root.find('other-charges')
        if charges_elem is not None:
            for charge_elem in charges_elem.findall('awb-other-charges'):
                charge = OtherCharge(
                    code=AWBParser._get_text(charge_elem, 'code'),
                    amount=AWBParser._get_float(charge_elem, 'amount'),
                    due=AWBParser._get_text(charge_elem, 'due'),
                    three_letter_code=AWBParser._get_text(charge_elem, 'three-letter-code'),
                )
                charges.append(charge)
        return charges
    
    @staticmethod
    def _parse_charges_summary(root: ET.Element) -> ChargesSummary:
        """Parse charges summary (weight-charge, tax, totals, etc.)."""
        summary = ChargesSummary()
        
        # Helper to get prepaid/collect values from string pairs
        def get_pair(tag: str) -> tuple:
            elem = root.find(tag)
            if elem is not None:
                strings = elem.findall('string')
                prepaid = 0.0
                collect = 0.0
                if len(strings) >= 1 and strings[0].text:
                    try:
                        prepaid = float(strings[0].text)
                    except ValueError:
                        pass
                if len(strings) >= 2 and strings[1].text:
                    try:
                        collect = float(strings[1].text)
                    except ValueError:
                        pass
                return prepaid, collect
            return 0.0, 0.0
        
        summary.weight_charge_prepaid, summary.weight_charge_collect = get_pair('weight-charge')
        summary.valuation_charge_prepaid, summary.valuation_charge_collect = get_pair('valuation-charge')
        summary.tax_prepaid, summary.tax_collect = get_pair('tax')
        summary.other_due_agent_prepaid, summary.other_due_agent_collect = get_pair('other-due-agent')
        summary.other_due_carrier_prepaid, summary.other_due_carrier_collect = get_pair('other-due-carrier')
        summary.total_prepaid, summary.total_collect = get_pair('weight-total')
        
        return summary
    
    @staticmethod
    def to_dict(details: AWBDetails) -> Dict[str, Any]:
        """Convert AWBDetails to dictionary for JSON serialization."""
        if not details:
            return {}
        
        return {
            "awb_type": details.awb_type,
            "airline_prefix": details.airline_prefix,
            "serial_number": details.serial_number,
            "hawb": details.hawb,
            "weight_payment_type": details.weight_payment_type,
            "other_charges_payment_type": details.other_charges_payment_type,
            "calculations": details.calculations,
            "shipper": {
                "details": details.shipper_details,
                "account": details.shipper_account,
            },
            "consignee": {
                "details": details.consignee_details,
                "account": details.consignee_account,
            },
            "agent": {
                "details": details.agent_details,
                "iata_code": details.agent_iata_code,
            },
            "issued_by": details.issued_by_details,
            "routing": {
                "departure": details.airport_departure,
                "departure_code": details.airport_departure_code,
                "destination": details.airport_destination,
                "to": details.route.to,
                "by": details.route.by,
                "flights": details.route.flights,
            },
            "rate_description": {
                "items": [asdict(item) for item in details.items],
                "total_pieces": details.total_pieces,
                "total_weight": details.total_weight,
                "weight_scale": details.weight_scale,
                "items_total": details.items_total,
            },
            "other_charges": [asdict(charge) for charge in details.other_charges],
            "charges_summary": asdict(details.charges_summary),
            "currency": details.currency,
            "insurance": details.insurance,
            "value_carrier": details.value_carrier,
            "value_customs": details.value_customs,
            "reference_number": details.reference_number,
            "handling_information": details.handling_information,
            "accounting_information": details.accounting_information,
            "sci": details.sci,
            "signatures": {
                "shipper": details.shipper_signature,
                "carrier": details.carrier_signature,
                "date": details.carrier_date,
                "place": details.carrier_place,
            },
            "notes": details.notes,
        }
