"""
Characters

Characters are (by default) Objects setup to be puppeted by Accounts.
They are what you "see" in game. The Character class in this module
is setup to be the "default" character type created by the default
creation commands.

"""
from evennia import DefaultCharacter
from utils.map import Mapper
from evennia import utils

import re

from evennia.utils import lazy_property
from world.handlers.traits import TraitHandler
from world.handlers.equip import EquipHandler 
import typeclasses.rooms

# Base statistics that every character gets.
BASE_STATS = {
    'hp' : { 'name':'HP', 'type':'gauge', 'base':100, 'max':'base'}, 
    'exp' : { 'name':'EXP', 'type':'gauge', 'base':0, 'max':'100' },
    'level' : { 'name':'Level', 'type':'static', 'base':1 }
}

CHARACTER_SLOTS = {
    "wield1" : None,
    "wield2" : None,
    "armor1" : None,
    "armor2" : None
}

CHARACTER_LIMBS = (
    ("right wield", ("wield1",)),
    ("left wield", ("wield2",)),
    ("body", ("body",)),
    ("legs", ("legs",)),
)

class Character(DefaultCharacter):
    """
    The Character defaults to reimplementing some of base Object's hook methods with the
    following functionality:

    at_basetype_setup - always assigns the DefaultCmdSet to this object type
                    (important!)sets locks so character cannot be picked up
                    and its commands only be called by itself, not anyone else.
                    (to change things, use at_object_creation() instead).
    at_after_move(source_location) - Launches the "look" command after every move.
    at_post_unpuppet(account) -  when Account disconnects from the Character, we
                    store the current location in the pre_logout_location Attribute and
                    move it to a None-location so the "unpuppeted" character
                    object does not need to stay on grid. Echoes "Account has disconnected" 
                    to the room.
    at_pre_puppet - Just before Account re-connects, retrieves the character's
                    pre_logout_location Attribute and move it back on the grid.
    at_post_puppet - Echoes "AccountName has entered the game" to the room.

    """

    def at_object_creation(self):
        "This is called when object is first created, only."

        # Set up the stats
        if (self.stats_base):
            # this will clear out all the stats!  Is there a better way to do this?
            self.stats_base.clear()
        for key, kwargs in BASE_STATS.iteritems():
            self.stats_base.add(key, **kwargs)

        # TODO: Move this to a separate data file.
        self.db.map_symbol = u'\u263b'.encode('utf-8')

        # For EquipmentHandler to work.
        self.db.slots = dict(CHARACTER_SLOTS)

        self.db.limbs = tuple(CHARACTER_LIMBS)

        return super(Character, self).at_object_creation()

    def at_before_move(self, dest):

        """
        Preferm pre-move steps.

        * Checks the room doesn't have any objects with mIsBlocking property.
          If it does, then it will return False so that account can not move
          there, unless they are an importal.
        """
        isBlocked = False

        # Search all objects in room
        allObjects = (con for con in dest.contents)

        roomBlockingObjects = dest.get_blocking_objects()

        # Filter out just things that actually block character
        actualBlockingObjects = []

        for con in roomBlockingObjects:
            if (hasattr(con.db, 'mIsBlocking') and con.db.mIsBlocking):
                isImmortal = False
                
                if self.locks.check_lockstring(self, "dummy:perm(Immortals)"):
                    isImmortal = True

                if (not isImmortal):
                    # Only block non-immortals
                    actualBlockingObjects.append(con)
                    self.msg("A %s blocks your path." % con.name)
                else:
                    self.msg("|yWARNING:|n You would have been blocked by a %s, but you are an "
                             "IMMORTAL!" % con.name)

        if (len(actualBlockingObjects) != 0):
            return False

        # Otherwise just do normal movement.
        return super(Character, self).at_before_move(dest)

     # Overload "search" to also allow the syntax <exit>.<object>

    def search(self, searchdata,
               global_search=False,
               use_nicks=True,  # should this default to off?
               typeclass=None,
               location=None,
               attribute_name=None,
               quiet=False,
               exact=False,
               candidates=None,
               nofound_string=None,
               multimatch_string=None,
               use_dbref=True):

        # Check if we have an exit pre-pended to the start of the command
        p = re.compile("(.+)\.(.+)")
        searchmatch = p.search(searchdata)
        
        if searchmatch:
            # We do have an exit pre-pended, let's extract it and then search
            # that location for the object we want.
            # We do this by
            # 1) stripping off the prepended location + "." from the object
            # 2) using the prepended location to search the "exits", and if
            # found, set the target of the search command there

            searchLocationString = None
            searchTarg = None

            searchLocationString = searchmatch.group(1)
            searchTarg = searchmatch.group(2)

            for ex in self.location.exits:
                if (ex.key == searchLocationString) or (searchLocationString in ex.aliases.all()):
                    location = ex.destination
                    searchdata = searchTarg
                    break

    
        return super(Character, self).search(searchdata, global_search,
                                             use_nicks, typeclass,
                                             location,
                                             attribute_name,
                                             quiet,
                                             exact,
                                             candidates,
                                             nofound_string,
                                             multimatch_string,
                                             use_dbref)
    def at_look(self, target):
        desc = super(Character, self).at_look(target)

        self.msg(type(target))
        if (utils.inherits_from(target, typeclasses.rooms.Room)):
            # Print out the map
            mapper = Mapper()
            mapper.generate_map(target) 
            
            desc = desc + "\n" + str(mapper)

        return desc

    # Pretty-print the equipment on this character.
    # TODO: Maybe move somewhere else
    def pp_equipment(self, looker):
        return self.equip.pretty_print(looker)

    @lazy_property
    def stats_base(self):
        return TraitHandler(self, db_attribute='stats_base')

    @lazy_property
    def equip(self):
        """Handler for equipped items"""
        return EquipHandler(self)


class Npc(Character):
    def at_char_entered(self, character):
        """
        A simple is_agressive check
        Can be expanded later
        """
        if self.db.is_aggressive:
            self.execute_cmd("say Graaah, die %s" % character)
        else:
            self.execute_cmd("say Greetings, %s" % character)

# TODO: Move to utils
# pretty-print the stats of the character.

