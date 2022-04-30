from __future__ import absolute_import
import edtime
from edrlog import EDRLog
from edri18n import _
EDRLOG = EDRLog()

class EDRFleetCarrier(object):
    def __init__(self):
        self.id = None
        self.callsign = None
        self.name = None
        self.access = "none"
        self.allow_notorious = False
        self._position = {"system": None, "body": None}
        self.departure = {"time": None, "destination": None}
        self.decommission_time = None
        self.purchase_orders = {}
        self.sale_orders = {}
        self.market_updated = False


    def __reset(self):
        self.id = None
        self.callsign = None
        self.name = None
        self.access = "none"
        self.allow_notorious = False
        self._position = {"system": None, "body": None}
        self.departure = {"time": None, "destination": None}
        self.decommission_time = None
        self.purchase_orders = {}
        self.sale_orders = {}
        self.market_updated = False


    def bought(self, buy_event):
        self.__reset()
        self.id = buy_event.get("CarrierID", None)
        self.callsign = buy_event.get("Callsign", None)
        self._position["system"] = buy_event.get("Location", None)

    def update_from_stats(self, fc_stats_event):
        if self.id and self.id != fc_stats_event.get("CarrierID", None):
            self.__reset()
        self.id = fc_stats_event.get("CarrierID", None)
        self.callsign = fc_stats_event.get("Callsign", None)
        self.name = fc_stats_event.get("Name", None)
        self.access = fc_stats_event.get("DockingAccess", "none")
        self.allow_notorious = fc_stats_event.get("AllowNotorious", False)

    def jump_requested(self, jump_request_event):
        if self.id and self.id != jump_request_event.get("CarrierID", None):
            self.__reset()
        self.id = jump_request_event.get("CarrierID", None)
        self.__update_position()
        request_time = edtime.EDTime()
        request_time.from_journal_timestamp(jump_request_event["timestamp"])
        jump_time = request_time.as_py_epoch() + 60*15
       
        self.departure = {
            "time": jump_time,
            "destination": jump_request_event.get("SystemName", None)
        }

    def jump_cancelled(self, jump_cancel_event):
        if self.id and self.id != jump_cancel_event.get("CarrierID", None):
            self.__reset()
        self.id = jump_cancel_event.get("CarrierID", None)
        self.departure = {"time": None, "destination": None}
        self.__update_position()

    @property
    def position(self):
        self.__update_position()
        return self._position["system"]

    def __update_position(self):
        now = edtime.EDTime.py_epoch_now()
        if self.decommission_time and now > self.decommission_time:
            self.__reset()
            return

        if self.is_parked():
            return
        
        if now < self.departure["time"]:
            return
        
        self._position["system"] = self.departure["destination"]
        self.departure = {"time": None, "destination": None}

    def update_docking_permissions(self, event):
        if self.id and self.id != event.get("CarrierID", None):
            self.__reset()
        self.id = event.get("CarrierID", None)
        self.access = event.get("DockingAccess", "none")
        self.allow_notorious = event.get("AllowNotorious", False)

    def update_from_jump_if_relevant(self, event):
        if self.id is None or self.id != event.get("MarketID", None):
            return
        self._position = {"system": event.get("StarSystem", None), "body": event.get("Body", None)}
        self.departure = {"time": None, "destination": None}

    def update_star_system_if_relevant(self, star_system, market_id, station_name):
        if market_id is None and station_name is None:
            return False
        if (self.id == market_id) or (self.callsign == station_name):
            self._position["system"] = star_system
            return True
        if (self.id == None) and market_id and station_name:
            self.id = market_id
            self.callsign = station_name
            self._position["system"] = star_system
            return True
        return False

    def cancel_decommission(self, event):
        if self.id and self.id != event.get("CarrierID", None):
            self.__reset()
        self.id = event.get("CarrierID", None)

    def decommission_requested(self, event):
        if self.id and self.id != event.get("CarrierID", None):
            self.__reset()
        self.id = event.get("CarrierID", None)
        self.decommission_time = event.get("ScrapTime", None)

    def is_parked(self):
        return self.departure["destination"] is None or self.departure["time"] is None

    def json_jump_schedule(self):
        self.__update_position()
        if self.id is None:
            return None

        if self.is_parked():
            return None

        return self.json_status()

    def json_status(self):
        self.__update_position()
        if self.id is None:
            return None

        return {
            "id": self.id,
            "callsign": self.callsign,
            "name": self.name,
            "from": self.position,
            "to": self.departure["destination"],
            "at": self.departure["time"] * 1000 if self.departure["time"] else None,
            "access": self.access,
            "allow_notorious": self.allow_notorious
        }

    # TODO see if market.json reflects the market of fleet carriers, including one's own
    # Market event + market.json file
    # perhaps tell the player if the market has a useful item (e.g. eng mats)
    # TODO hint about complementing certain blueprints/upgrade/pinned odyssey things?
    # TODO timestamp on market orders
    def trade_order(self, entry):
        if entry.get("event", None) != "CarrierTradeOrder":
            return False

        if entry.get("Commodity", None) is None:
            return False
        
        item = entry["Commodity"]
        if entry.get("CarrierID", None) != self.id:
            return False
        
        if entry.get("CancelTrade",False) == True:
            return self.__cancel_order(item)

        if entry.get("PurchaseOrder", 0) > 0:
            return self.__purchase_order(item, entry.get("Commodity_Localised", item), entry["Price"], entry["PurchaseOrder"])

        if entry.get("SaleOrder", 0) > 0:
            return self.__sale_order(item, entry.get("Commodity_Localised", item), entry["Price"], entry["SaleOrder"])
        
    def __cancel_order(self, item):
        try:
            del self.sale_orders[item]
            self.market_updated = True
        except:
            pass

        try:
            del self.purchase_orders[item]
            self.market_updated = True
        except:
            pass
    
    def __purchase_order(self, item, localized_item, price, quantity):
        self.purchase_orders[item] = {"price": price, "quantity": quantity, "l10n": localized_item}
        self.market_updated = True
        try:
            del self.sale_orders[item]
        except:
            pass

    def __sale_order(self, item, localized_item, price, quantity):
        self.sale_orders[item] = {"price": price, "quantity": quantity, "l10n": localized_item}
        self.market_updated = True
        try:
            del self.purchase_orders[item]
        except:
            pass
    
    def json_market(self):
        self.__update_position()
        if self.id is None:
            return None

        return {
            "id": self.id,
            "callsign": self.callsign,
            "name": self.name,
            "location": self.position,
            "access": self.access,
            "allow_notorious": self.allow_notorious,
            "sales": self.sale_orders,
            "purchases": self.purchase_orders
        }

    def text_market(self, timeframe=None):
        # TODO within timeframe
        self.__update_position()
        if self.id is None:
            return None

        header = _("Fleet Carrier Market Info")
        key_info = _("Callsign:  \t{}\nName:      \t{}\nLocation:  \t{}\nAccess:    \t{}\nNotorious: \t{}").format(self.callsign, self.name, self.position, self.access, _("allowed") if self.allow_notorious else _("disallowed"))
        details_purchases = []
        details_sales = []
        for order in self.purchase_orders:
            quantity = self.purchase_orders[order]["quantity"]
            item = self.purchase_orders[order]["l10n"][:30]
            price = self.purchase_orders[order]["price"]
            details_purchases.append(f'{quantity: >8} {item: <30} {price: >10n}')

        # TODO not used
        headers = [_("Item"), _("Price"), _("Quantity")]
        
        for order in self.sale_orders:
            quantity = self.sale_orders[order]["quantity"]
            item = self.sale_orders[order]["l10n"][:30]
            price = self.sale_orders[order]["price"]
            details_sales.append(f'{quantity: >8} {item: <30} {price: >10n}')

        summary = header
        summary += "\n"
        summary += key_info
        summary += "\n"
        if details_sales:
            summary += "\n"
            summary += _("[Selling]\n")
            summary += _(f'{"Quantity": >8} {"Item": <30} {"Price (cr)": >10}\n')
            summary += "\n".join(details_sales)
            summary += "\n"
        if details_purchases:
            summary += "\n"
            summary += _("[Buying]\n")
            summary += _(f'{"Quantity": >8} {"Item": <30} {"Price (cr)": <10}\n')
            summary += "\n".join(details_purchases)
            summary += "\n"
        
        return summary

    def acknowledge_market(self):
        self.market_updated = False

    def has_market_changed(self):
        return self.market_updated

    def tweak_crew_service(self, entry):
        if entry.get("event", None) != "CarrierCrewServices":
            return False

        if entry.get("CarrierID", None) != self.id:
            return False

        service = entry.get("CrewRole", None)
        operation = entry.get("Operation", None)
        crew = entry.get("CrewName", None)
        if not (service and operation and crew):
            return False
        ops_LUT = {
            "replace": "open", # TODO not sure
            "activate": "open",
            "deactivate": "n/a",
            "pause": "closed",
            "resume": "open"
        }
        state = ops_LUT.get(operation.lower(), "??? ({})".format(operation.lower()))
        if operation.lower() == "replace":
            if self.services[service.lower()]:
                self.services[service.lower()]["crew"] = crew
            else:
                self.services[service.lower()] = {"state": state, "crew": crew}
        else:
            self.services[service.lower()] = {"state": state, "crew": crew}