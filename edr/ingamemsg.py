# coding= utf-8
import os
import sys
import math

import igmconfig
import edrlog
import textwrap
from edri18n import _
import utils2to3

EDRLOG = edrlog.EDRLog()

_overlay_dir = utils2to3.pathmaker(__file__, u'EDMCOverlay')

if _overlay_dir not in sys.path:
    sys.path.append(_overlay_dir)

try:
    import edmcoverlay
except ImportError:
    raise Exception(str(sys.path))

import lrucache

class InGameMsg(object):   
    MESSAGE_KINDS = [ "intel", "warning", "sitrep", "notice", "help", "navigation", "docking"]
    LEGAL_KINDS = ["intel", "warning"] 

    def __init__(self):
        self._overlay = edmcoverlay.Overlay()
        self.cfg = {}
        self.general_config()
        self.must_clear = False
        for kind in self.MESSAGE_KINDS:
            self.message_config(kind)
        for kind in self.LEGAL_KINDS:
            self.legal_config(kind)
        self.docking_config()
        self.msg_ids = lrucache.LRUCache(1000, 60*15)

    def general_config(self):
        conf = igmconfig.IGMConfig()
        self.cfg["general"] = {
            "large" : {
                "h": conf.large_height(),
                "w": conf.large_width()
            },
            "normal" : {
                "h": conf.normal_height(),
                "w": conf.normal_width()
            }
        }

    def message_config(self, kind):
        conf = igmconfig.IGMConfig() 
        self.cfg[kind] = {
            "h": {
                "x": conf.x(kind, "header"),
                "y": conf.y(kind, "header"),
                "ttl": conf.ttl(kind, "header"),
                "rgb": conf.rgb(kind, "header"),
                "size": conf.size(kind, "header"),
                "len": conf.len(kind, "header"),
                "align": conf.align(kind, "header")
            },
            "b": {
                "x": conf.x(kind, "body"),
                "y": conf.y(kind, "body"),
                "ttl": conf.ttl(kind, "body"),
                "rgb": conf.rgb(kind, "body"),
                "size": conf.size(kind, "body"),
                "len": conf.len(kind, "body"),
                "align": conf.align(kind, "body"),
                "rows": conf.body_rows(kind),
                "cache": lrucache.LRUCache(conf.body_rows(kind), conf.ttl(kind, "body")),
                "last_row": 0
            }
        }
        if not conf.panel(kind):
            return
        self.cfg[kind]["panel"] = {
            "x": conf.x(kind, "panel"),
            "y": conf.y(kind, "panel"),
            "x2": conf.x2(kind, "panel"),
            "y2": conf.y2(kind, "panel"),
            "ttl": conf.ttl(kind, "panel"),
            "rgb": conf.rgb(kind, "panel"),
            "fill": conf.fill(kind, "panel")
        }

    def legal_config(self, kind):
        conf = igmconfig.IGMConfig() 
        kind = u"{}-legal".format(kind)
        self.cfg[kind] = {
            "enabled": conf._getboolean(kind, "enabled"),
            "clean": {
                "x": conf.x(kind, "clean"),
                "y": conf.y(kind, "clean"),
                "h": conf.h(kind, "clean_bar"),
                "w": conf.w(kind, "clean_bar"),
                "s": conf.s(kind, "clean_bar"),
                "ttl": conf.ttl(kind, "clean"),
                "rgb": conf.rgb_list(kind, "clean"),
                "fill": conf.fill_list(kind, "clean"),
            },
            "wanted": {
                "x": conf.x(kind, "wanted"),
                "y": conf.y(kind, "wanted"),
                "h": conf.h(kind, "wanted_bar"),
                "w": conf.w(kind, "wanted_bar"),
                "s": conf.s(kind, "wanted_bar"),
                "ttl": conf.ttl(kind, "wanted"),
                "rgb": conf.rgb_list(kind, "wanted"),
                "fill": conf.fill_list(kind, "wanted"),
            },
            "bounties": {
                "x": conf.x(kind, "bounties"),
                "y": conf.y(kind, "bounties"),
                "h": conf.h(kind, "bounties_bar"),
                "w": conf.w(kind, "bounties_bar"),
                "s": conf.s(kind, "bounties_bar"),
                "ttl": conf.ttl(kind, "bounties"),
                "rgb": conf.rgb_list(kind, "bounties"),
                "fill": conf.fill_list(kind, "bounties"),
            },
        }
        if not conf.panel(kind):
            return
        self.cfg[kind]["panel"] = {
            "x": conf.x(kind, "panel"),
            "y": conf.y(kind, "panel"),
            "x2": conf.x2(kind, "panel"),
            "y2": conf.y2(kind, "panel"),
            "ttl": conf.ttl(kind, "panel"),
            "rgb": conf.rgb(kind, "panel"),
            "fill": conf.fill(kind, "panel")
        }

    def docking_config(self):
        conf = igmconfig.IGMConfig()
        kind = "docking-station" 
        self.cfg[kind] = {
            "enabled": conf._getboolean(kind, "enabled"),
            "schema": {
                "x": conf.x(kind, "schema"),
                "y": conf.y(kind, "schema"),
                "h": conf.h(kind, "schema"),
                "w": conf.w(kind, "schema"),
                "ttl": conf.ttl(kind, "schema"),
                "rgb": conf.rgb_list(kind, "schema"),
                # TODO green, red, rack, pads? list
                "fill": conf.fill_list(kind, "schema"),
                # TODO large, small, medium, highglights? fill list
            }
        }
        if not conf.panel(kind):
            return
        self.cfg[kind]["panel"] = {
            "x": conf.x(kind, "panel"),
            "y": conf.y(kind, "panel"),
            "x2": conf.x2(kind, "panel"),
            "y2": conf.y2(kind, "panel"),
            "ttl": conf.ttl(kind, "panel"),
            "rgb": conf.rgb(kind, "panel"),
            "fill": conf.fill(kind, "panel")
        }


    def intel(self, header, details, legal=None):
        self.__clear_if_needed()
        if "panel" in self.cfg["intel"]:
            self.__shape("intel", self.cfg["intel"]["panel"])
        kind_legal = u"intel-legal"
        if "panel" in self.cfg[kind_legal] and self.cfg[kind_legal].get("enabled", False):
            self.__shape(kind_legal, self.cfg[kind_legal]["panel"])
        self.__msg_header("intel", header)
        self.__msg_body("intel", details)
        
        if not self.cfg["intel-legal"].get("enabled", None):
            return
        if not legal:
            legal = { "clean": [0]*12, "wanted": [0]*12, "bounties": [0]*12 }
        self.__legal_vizualization(legal, "intel")
        

    def warning(self, header, details, legal=None):
        self.__clear_if_needed()
        if "panel" in self.cfg["warning"]:
            self.__shape("warning", self.cfg["warning"]["panel"])
        kind_legal = u"warning-legal"
        if "panel" in self.cfg[kind_legal] and self.cfg[kind_legal].get("enabled", False):
            self.__shape(kind_legal, self.cfg[kind_legal]["panel"])
        self.__msg_header("warning", header)
        self.__msg_body("warning", details)
        if not self.cfg["warning-legal"].get("enabled", None):
            return
        if not legal:
            legal = { "clean": [0]*12, "wanted": [0]*12, "bounties": [0]*12 }
        self.__legal_vizualization(legal, "warning")

    def notify(self, header, details):
        self.__clear_if_needed()
        if "panel" in self.cfg["notice"]:
            self.__shape("notify", self.cfg["notify"]["panel"])
        self.__msg_header("notice", header)
        self.__msg_body("notice", details)
    
    def help(self, header, details):
        self.__clear_if_needed()
        if "panel" in self.cfg["help"]:
            self.__shape("help", self.cfg["help"]["panel"])
        self.__msg_header("help", header)
        self.__msg_body("help", details)
        self.must_clear = True

    def sitrep(self, header, details):
        self.__clear_if_needed()
        self.__clear_kind("sitrep")
        if "panel" in self.cfg["sitrep"]:
            self.__shape("sitrep", self.cfg["sitrep"]["panel"])
        self.__msg_header("sitrep", header)
        self.__msg_body("sitrep", details)

    def navigation(self, bearing, destination, distance=None, pitch=None):
        self.clear_navigation()
        if "panel" in self.cfg["navigation"]:
            self.__shape("navigation", self.cfg["navigation"]["panel"])
        header = u"› {:03} ‹     ↓ {:02} ↓".format(bearing, pitch) if pitch else u"> {:03} <".format(bearing)
        details = [destination.title] if destination.title else []
        if distance:
            details.append(_(u"Dis: {}km".format(int(distance))))
        details.append(_(u"Lat: {:.4f}".format(destination.latitude)))
        details.append(_(u"Lon: {:.4f}".format(destination.longitude)))
        self.__msg_header("navigation", header)
        self.__msg_body("navigation", details)

    def docking(self, station, pad):
        self.clear_docking()
        if not station:
            return
        if "panel" in self.cfg["docking"]:
            self.__shape("docking", self.cfg["docking"]["panel"])
        if "panel" in self.cfg["docking-station"] and self.cfg["docking-station"].get("enabled", False):
            self.__shape("docking-station", self.cfg["docking-station"]["panel"])
        economy = u"{}/{}".format(station["economy"], station["secondEconomy"]) if station["secondEconomy"] else station["economy"]
        header = u"{} ({})".format(station["name"], economy)
        details = []
        a = u"◌" if station.get("type","N/A").lower() in ["outpost"] else u"●" # ■□●◌
        b = u"●" if "haveShipyard" in station else u"◌"
        c = u"●" if "haveOutfitting" in station else u"◌"
        details.append(u"LG. Pad:{}   Outfit:{}   Shipyard:{}".format(a,b,c))
        a = u"●" if "Refuel" in station["otherServices"] else u"◌"
        b = u"●" if "Repair" in station["otherServices"] else u"◌"
        c = u"●" if "Restock" in station["otherServices"] else u"◌"
        details.append(u"Refuel:{}   Repair:{}   Restock:{}".format(a,b,c))
        a = u"●" if "haveMarket" in station else u"◌"
        b = u"●" if "Black Market" in station["otherServices"] else u"◌"
        c = u"◌"
        m = u"M." 
        if "Material Trader" in station["otherServices"]:
            c = u"●"
            if station['economy']:
                if station['economy'].lower() in ['extraction', 'refinery']:
                    m = u"RAW"
                elif station['economy'].lower() == 'industrial':
                    m = u"MAN"
                elif station['economy'].lower() in ['high tech', 'military']:
                    m = "ENC"
        details.append(u"Market:{}   B.Market:{}   {} Trad:{}".format(a,b,m,c))
        a = u"●" if "Interstellar Factors Contact" in station["otherServices"] else u"◌"
        b = u"●" if "Technology Broker" in station["otherServices"] else u"◌"
        details.append(u"I.Factor:{}   T.Broker:{}".format(a,b))
        details.append(u"as of {date}".format(date=station['updateTime']['information']))
        self.__msg_header("docking", header)
        self.__msg_body("docking", details)
        if station["type"] and station["type"].lower() in ["asteroid base", 'bernal starport', "coriolis starport", "ocellus starport", "orbis starport"]:
            self.__station_schematic(pad)
        else:
            print "dummy" # TODO N/A graphic, simplified icon ?

    
    def __station_schematic(self, landing_pad):
        cfg = self.cfg[u"docking-station"]
        x = cfg["schema"]["x"]
        y = cfg["schema"]["y"]
        w = cfg["schema"]["w"]
        h = cfg["schema"]["h"]

        '''
        bar = {
            "x": 0,
            "y": 0,
            "x2": 0,
            "y2": 0,
            "rgb": "#000000",
            "fill": "#000000",
            "ttl": 0,
        }
        '''

        xscale = h # TODO
        yscale = w # TODO
        cx = int(round(x + w/2.0))
        cy = int(round(y + h/2.0))
        
        red_light = {
            "x": int(x),
            "y": int(cy - (0.12962962962962962962962962962963 * yscale)),
            "x2": max(1, int(0.03125 * xscale)),
            "y2": max(1,int(2.0*0.12962962962962962962962962962963 * yscale)),
            "rgb": "#FF0000",
            "fill": "#FF0000",
            "ttl": cfg["schema"]["ttl"],
        }
        print(red_light)
        self.__shape(u"station-redlight", red_light)

        green_light = {
            "x": int(x+w-(0.03125 * xscale)),
            "y": int(cy - (0.12962962962962962962962962962963 * yscale)),
            "x2": max(1,int(0.03125 * xscale)),
            "y2": max(1, int(2.0*0.12962962962962962962962962962963 * yscale)),
            "rgb": "#00FF00",
            "fill": "#00FF00",
            "ttl": cfg["schema"]["ttl"],
        }
        print(green_light)
        self.__shape(u"station-greenlight", green_light)

        '''
        toaster = {
            "x": int(x),
            "y": int(cy - (0.14814814814814814814814814814815 * yscale)),
            "x2": max(1,int(w)),
            "y2": max(1,int(0.14814814814814814814814814814815 * yscale)),
            "rgb": "#DDDDDD",
            "fill": "",
            "ttl": cfg["schema"]["ttl"],
        }
        print(toaster)
        self.__shape(u"station-redlight", toaster)
        '''
        # dodecaedron
        alpha = math.radians(15)
        sin15 = math.sin(alpha)
        cos15 = math.cos(alpha)
        sin45 = math.sqrt(2) / 2
        sin60 = math.sqrt(3) / 2
        dodecagon = [
            (cos15, sin15),
            (cos15, -sin15),
            (sin45, -sin45),
            (sin15, -cos15),
            (-sin15, -cos15),
            (-sin45, -sin45),
            (-cos15, -sin15),
            (-cos15, sin15),
            (-sin45, sin45),
            (-sin15, cos15),
            (sin15, cos15),
            (sin45, sin45),
            (cos15, sin15),
        ]

        # TODO colors, need more. 6?
        radials = {
            "outer": [],
            "inner": []
        }
        scales = [1.0, 0.7, 0.25]
        i = 0
        for s in scales:
            rx = 1.0*s*w/2.0
            ry = 1.0*s*h/2.0
            points = []
            for (dx, dy) in dodecagon:
                x = int(round(cx + dx*rx))
                y = int(round(cy + dy*ry))
                points.append({"x": x, "y": y})
            if s == scales[0]:
                radials["outer"] = points
            elif s == scales[-1]:
                radials["inner"] = points
            wireframe = {
                "id": "station-wireframe-{}".format(s),
                "color": cfg["schema"]["rgb"][2+i],
                "shape": "vect",
                "ttl": cfg["schema"]["ttl"],
                "vector": points
            }
            self._overlay.send_raw(wireframe)
            i = i+1

        i = 0
        for s in [scales[0]-(scales[0]-scales[1])/2.0, scales[1]-(scales[1]-scales[2])*2.0/3.0]:
            points = []
            rx = 1.0*s*w/2.0
            ry = 1.0*s*h/2.0
            for (dx, dy) in dodecagon[0:4]:
                x = int(round(cx + dx*rx))
                y = int(round(cy + dy*ry))
                points.append({"x": x, "y": y})
            wireframe = {
                "id": "station-wireframe-1-{}".format(s),
                "color": cfg["schema"]["rgb"][2+i],
                "shape": "vect",
                "ttl": cfg["schema"]["ttl"],
                "vector": points
            }
            self._overlay.send_raw(wireframe)
            
            points = []
            for (dx, dy) in dodecagon[4:8]:
                x = int(round(cx + dx*rx))
                y = int(round(cy + dy*ry))
                points.append({"x": x, "y": y})
            wireframe = {
                "id": "station-wireframe-2-{}".format(s),
                "color": cfg["schema"]["rgb"][2+i],
                "shape": "vect",
                "ttl": cfg["schema"]["ttl"],
                "vector": points
            }
            self._overlay.send_raw(wireframe)

            points = []
            for (dx, dy) in dodecagon[8:12]:
                x = int(round(cx + dx*rx))
                y = int(round(cy + dy*ry))
                points.append({"x": x, "y": y})
            wireframe = {
                "id": "station-wireframe-3-{}".format(s),
                "color": cfg["schema"]["rgb"][2+i],
                "shape": "vect",
                "ttl": cfg["schema"]["ttl"],
                "vector": points
            }
            self._overlay.send_raw(wireframe)
            i = i+1

        s = scales[1]-(scales[1]-scales[2])/3.0
        rx = 1.0*s*w/2.0
        ry = 1.0*s*h/2.0
        points = []
        for (dx, dy) in dodecagon[2:4]:
            x = int(round(cx + dx*rx))
            y = int(round(cy + dy*ry))
            points.append({"x": x, "y": y})
        wireframe = {
            "id": "station-wireframe-1-{}".format(s),
            "color": cfg["schema"]["rgb"][3],
            "shape": "vect",
            "ttl": cfg["schema"]["ttl"],
            "vector": points
        }
        self._overlay.send_raw(wireframe)
        
        points = []
        for (dx, dy) in dodecagon[6:8]:
            x = int(round(cx + dx*rx))
            y = int(round(cy + dy*ry))
            points.append({"x": x, "y": y})
        wireframe = {
            "id": "station-wireframe-2-{}".format(s),
            "color": cfg["schema"]["rgb"][3],
            "shape": "vect",
            "ttl": cfg["schema"]["ttl"],
            "vector": points
        }
        self._overlay.send_raw(wireframe)

        points = []
        for (dx, dy) in dodecagon[10:12]:
            x = int(round(cx + dx*rx))
            y = int(round(cy + dy*ry))
            points.append({"x": x, "y": y})
        wireframe = {
            "id": "station-wireframe-3-{}".format(s),
            "color": cfg["schema"]["rgb"][3],
            "shape": "vect",
            "ttl": cfg["schema"]["ttl"],
            "vector": points
        }
        self._overlay.send_raw(wireframe)
        
        for o,i in zip(radials["outer"], radials["inner"]):
            wireframe = {
                "id": "station-radial-{}-{}-{}-{}".format(o["x"], o["y"], i["x"], i["y"]),
                "color": cfg["schema"]["rgb"][2],
                "shape": "vect",
                "ttl": cfg["schema"]["ttl"],
                "vector": [o,i]
            }
            self._overlay.send_raw(wireframe)
        sectors = [
            ( 0, +1), (-0.5, sin60), (-sin60, +0.5),
            (-1,  0), (-sin60, -0.5), (-0.5, -sin60),
            ( 0, -1), (+0.5, -sin60), (sin60, -0.5),
            (+1,  0), (sin60, +0.5), (+0.5, sin60),
        ]


        # higlight of landing pad with size


    def __legal_vizualization(self, legal, kind):
        cleans = legal["clean"]
        wanteds = legal["wanted"]
        bounties = legal["bounties"]
        cfg = self.cfg[u"{}-legal".format(kind)]
        maxBounty = max(bounties)
        maxCW = max(cleans + wanteds)
        ystep = {"clean": maxCW / float(cfg["clean"]["h"]), "wanted": maxCW / float(cfg["wanted"]["h"]), "bounties": maxBounty / float(cfg["bounties"]["h"])} 
        x = {"clean": 0, "wanted": 0, "bounties": 0}
        y = 0
        h = 0
        m = 0

        bar = {
            "x": 0,
            "y": 0,
            "x2": 0,
            "y2": 0,
            "rgb": "#000000",
            "fill": "#000000",
            "ttl": 0,
        }

        for clean, wanted, bounty in zip(cleans, wanteds, bounties):
            dx = cfg["clean"]["x"]
            dy = cfg["clean"]["y"]
            h = max(clean/ystep["clean"],1) if clean else 1
            y = cfg["clean"]["h"] - h
            bar["x"] = int(x["clean"]+dx)
            bar["y"] =int(dy-h)
            bar["x2"] = int(cfg["clean"]["w"])
            bar["y2"] = dy - bar["y"]
            bar["rgb"] = cfg["clean"]["rgb"][m] or self.__cleancolor(clean, kind) 
            bar["fill"] = self.__cleancolor(clean, kind)
            bar["ttl"] = cfg["clean"]["ttl"]
            self.__shape(u"{}-clean-bar".format(kind), bar)

            dx = cfg["wanted"]["x"]
            dy = cfg["wanted"]["y"]
            h = max(wanted/ystep["wanted"], 1) if wanted else 1
            y = 0
            bar["x"] = int(x["wanted"]+dx)
            bar["y"] = int(y+dy)
            bar["x2"] = int(cfg["wanted"]["w"])
            bar["y2"] = int(h)
            bar["rgb"] = cfg["wanted"]["rgb"][m] or self.__wantedcolor(wanted, kind) 
            bar["fill"] = self.__wantedcolor(wanted, kind)
            bar["ttl"] = cfg["wanted"]["ttl"]
            self.__shape(u"{}-wanted-bar".format(kind), bar)

            dx = cfg["bounties"]["x"]
            dy = cfg["bounties"]["y"]
            h = max(bounty/ystep["bounties"],1) if bounty else 1
            y = cfg["bounties"]["h"] - h
            bar["x"] = int(x["bounties"]+dx)
            bar["y"] = int(dy-h)
            bar["x2"] = int(cfg["bounties"]["w"])
            bar["y2"] = dy - bar["y"]
            bar["rgb"] = cfg["bounties"]["rgb"][m] or self.__bountycolor(bounty, kind) 
            bar["fill"] = self.__bountycolor(bounty, kind)
            bar["ttl"] = cfg["bounties"]["ttl"]
            self.__shape("{}-bounty-bar".format(kind), bar)

            x = {category: x[category] + cfg[category]["w"] + cfg[category]["s"] for category in x}
            m += 1

    def clear(self):
        for msg_id in self.msg_ids.keys():
            self.__clear(msg_id)
        self.msg_ids.reset()
        self.must_clear = False

    def clear_intel(self):
        self.__clear_kind("intel")
    
    def clear_sitrep(self):
        self.__clear_kind("sitrep")

    def clear_notice(self):
        self.__clear_kind("notice")
    
    def clear_warning(self):
        self.__clear_kind("warning")

    def clear_navigation(self):
        self.__clear_kind("navigation")

    def clear_docking(self):
        self.__clear_kind("docking")

    def __clear_kind(self, kind):
        tag = "EDR-{}".format(kind)
        for msg_id in self.msg_ids.keys():
            if msg_id.startswith(tag):
                self.__clear(msg_id)
                self.msg_ids.evict(msg_id)

    def __clear_if_needed(self):
        if self.must_clear:
            self.clear()
    
    def __wrap_body(self, kind, lines):
        if not lines:
            return []
        chunked_lines = []
        rows = self.cfg[kind]["b"]["rows"]
        rows_per_line = max(1, rows / len(lines))
        bonus_rows = rows % len(lines)
        for line in lines:
            max_rows = rows_per_line
            if bonus_rows:
                max_rows += 1
            wrapped_text = self.__wrap_text(kind, "b", line, max_rows)
            if bonus_rows and wrapped_text == max_rows:
               bonus_rows -= 1
            chunked_lines.append(wrapped_text)
            if len(chunked_lines) >= rows:
                break
        return chunked_lines

    def __wrap_text(self, kind, part, text, max_rows):
        EDRLOG.log(u"text: {}".format(text), "DEBUG")
        if text is None:
            return None
        width = self.cfg[kind][part]["len"]
        wrapper = textwrap.TextWrapper(width=width, subsequent_indent="  ", break_on_hyphens=False)
        return wrapper.wrap(text)[:max_rows]

    def __adjust_x(self, kind, part, text):
        conf = self.cfg[kind][part]
        x = conf["x"]
        if conf["align"] == "center":
            w = self.cfg["general"][conf["size"]]["w"]
            text_w = len(text)*w
            return max(0,int(x-text_w/2.0))
        return x

    def __msg_header(self, kind, header, timeout=None):
        conf = self.cfg[kind]["h"]
        ttl = timeout if timeout else conf["ttl"]
        text = header[:conf["len"]]
        x = self.__adjust_x(kind, "h", text)
        EDRLOG.log(u"header={}, row={}, col={}, color={}, ttl={}, size={}".format(header, conf["y"], x, conf["rgb"], ttl, conf["size"]), "DEBUG")
        self.__display(kind, text, row=conf["y"], col=x, color=conf["rgb"], ttl=ttl, size=conf["size"])

    def __msg_body(self, kind, body, timeout=None):
        conf = self.cfg[kind]["b"]
        ttl = timeout if timeout else conf["ttl"]
        x = conf["x"]
        chunked_lines = self.__wrap_body(kind, body)
        
        for chunked_line in chunked_lines:
            if chunked_line is None:
                continue
            for chunk in chunked_line:
                row_nb = self.__best_body_row(kind, chunk)
                y = conf["y"] + row_nb * self.cfg["general"][conf["size"]]["h"]
                conf["cache"].set(row_nb, chunk)
                x = self.__adjust_x(kind, "b", chunk)
                EDRLOG.log(u"line={}, rownb={}, last_row={}, row={}, col={}, color={}, ttl={}, size={}".format(chunk, row_nb, conf["last_row"], y, x, conf["rgb"], ttl, conf["size"]), "DEBUG")
                self.__display(kind, chunk, row=y, col=x, color=conf["rgb"], size=conf["size"], ttl=ttl)
                self.__bump_body_row(kind)

    def __best_body_row(self, kind, text):
        rows = range(self.cfg[kind]["b"]["rows"])
        used_rows = []
        for row_nb in rows:
            cached = self.cfg[kind]["b"]["cache"].get(row_nb)
            used_rows.append(row_nb)
            if (cached is None or cached == text):
                return row_nb
        
        remaining_rows = (set(rows) - set(used_rows))
        if len(remaining_rows):
            return remaining_rows.pop()
        else:
            self.__bump_body_row(kind)
            return self.cfg[kind]["b"]["last_row"]

    def __bump_body_row(self, kind):
        self.cfg[kind]["b"]["last_row"] += 1
        if self.cfg[kind]["b"]["last_row"] > self.cfg[kind]["b"]["rows"]:
            self.cfg[kind]["b"]["last_row"] = 0


    def __display(self, kind, text, row, col, color="#dd5500", size="large", ttl=5):
        try:
            msg_id = "EDR-{}-{}".format(kind, row)
            self._overlay.send_message(msg_id, text, color, int(col), int(row), ttl=ttl, size=size)
            self.msg_ids.set(msg_id, ttl)
        except:
            EDRLOG.log(u"In-Game Message failed.", "ERROR")
            pass

    def __shape(self, kind, panel):
        try:
            shape_id = "EDR-{}-{}-{}-{}-{}-shape".format(kind, panel["x"], panel["y"], panel["x2"], panel["y2"])
            print(shape_id)
            self._overlay.send_shape(shape_id, "rect", panel["rgb"], panel["fill"], panel["x"], panel["y"], panel["x2"], panel["y2"], ttl=panel["ttl"])
            self.msg_ids.set(shape_id, panel["ttl"])
        except:
            EDRLOG.log(u"In-Game Shape failed.", "ERROR")
            pass

    def __clear(self, msg_id):
        try:
            self._overlay.send_message(msg_id, "", "", 0, 0, 0, 0)
            self.msg_ids.evict(msg_id)
            self.__reset_caches() # TODO maybe that's too much
        except:
            EDRLOG.log(u"In-Game Message failed to clear {}.".format(msg_id), "ERROR")
            pass
    
    def __reset_caches(self):
        for kind in self.MESSAGE_KINDS:
            self.cfg[kind]["b"]["cache"].reset()
    
    def __bountycolor(self, bounty, kind):
        kind = u"{}-legal".format(kind)
        cfg = self.cfg[kind]["bounties"]
        if bounty > 0:
            try:
                order_of_magnitude = int(math.log10(max(bounty,1)/100.0))
                index = max(1, min(order_of_magnitude+1, len(cfg["fill"])-1 ))
                return cfg["fill"][index]
            except:
                return cfg["fill"][1]
        return cfg["fill"][0]

    def __cleancolor(self, clean, kind):
        kind = u"{}-legal".format(kind)
        cfg = self.cfg[kind]["clean"]
        if clean > 0:
            try:
                order_of_magnitude = int(math.log10(max(clean,1)))
                index = max(1, min(order_of_magnitude+1, len(cfg["fill"])-1 ))
                return cfg["fill"][index]
            except:
                return cfg["fill"][1]
        return cfg["fill"][0]
    
    def __wantedcolor(self, wanted, kind):
        kind = u"{}-legal".format(kind)
        cfg = self.cfg[kind]["wanted"]
        if wanted > 0:
            try:
                order_of_magnitude = int(math.log10(max(wanted,1)))
                index = max(1, min(order_of_magnitude+1, len(cfg["fill"])-1 ))
                return cfg["fill"][index]
            except:
                return cfg["fill"][1]
        return cfg["fill"][0]

    def shutdown(self):
        # TODO self._overlay.shutdown() or something
        return
