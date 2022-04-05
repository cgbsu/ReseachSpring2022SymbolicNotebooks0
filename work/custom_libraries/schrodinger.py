import sympy as sp
import sympy.physics.units.quantities as sq
from sympy.physics.quantum.constants import hbar
from custom_libraries.stepper import *

PSI_FUNCTION = sp.Function( "psi" )
POTENTIAL_FUNCTION = sp.Function( "V" )
TOTAL_ENERGY_SYMBOL = sq.Symbol( 'E', nonzero = True, positive = True )
MASS_SYMBOL = sq.Quantity( 'm', positive = True, nonzero = True )
POSITION_SYMBOL = sp.Symbol( 'x', positive = True )

def time_independent_schroedinger_equation_1d( 
            psi = PSI_FUNCTION, 
            potential = POTENTIAL_FUNCTION, 
            total_energy = TOTAL_ENERGY_SYMBOL, 
            mass = MASS_SYMBOL, 
            reduced_planck_constant = hbar, 
            position = POSITION_SYMBOL 
        ): 
    return sp.Eq( 
            ( ( -( reduced_planck_constant ** 2 ) / ( 2 * mass ) ) \
                    * sp.Derivative( psi( position ), ( position, 2 ) ) )
                    + ( potential( position ) * psi( position ) ), 
            total_energy * psi( position ) 
        )

class ZeroPotential( sp.Function ): 
    @classmethod
    def eval( cls, position ):
        return 0

#https://docs.sympy.org/latest/modules/assumptions/index.html#querying
#https://docs.sympy.org/latest/modules/codegen.html#module-sympy.codegen.cxxnodes

class Potential( sp.Function ): 
    DEFAULT_POTENTIAL = sp.Symbol( "V_0" )
    @classmethod
    def eval( cls, position, potential = DEFAULT_POTENTIAL ): 
        return potential

class TunnelPotential( sp.Function ): 
    DEFAULT_WELL_LENGTH = sp.Symbol( 'L' )
    DEFAULT_POTENTIAL = Potential.DEFAULT_POTENTIAL
    DEFAULT_START = 0
    @classmethod
    def eval( cls, position, length = DEFAULT_WELL_LENGTH, 
             start = DEFAULT_START, potential = DEFAULT_POTENTIAL ): 
        if position < start or position > sp.simplify( length + start ): 
            return ZeroPotential.eval( position )
        return Potential.eval( position, potential )

class StairWell( sp.Function ): 
    UNIFORM_LENGTH_SYMBOL = sp.Symbol( 'L' )
    UNIFORM_POTENTIAL_SYMBOL = sp.Symbol( 'V' )
    UNIFORM_STAIR_LENGTHS = ( 
            UNIFORM_LENGTH_SYMBOL, 
            UNIFORM_LENGTH_SYMBOL, 
            UNIFORM_LENGTH_SYMBOL 
        )
    UNIFORM_POTENTIALS = ( 
            UNIFORM_POTENTIAL_SYMBOL, 
            2 * UNIFORM_POTENTIAL_SYMBOL / 3, 
            UNIFORM_POTENTIAL_SYMBOL / 3
        )
    NON_UNIFORM_STAIR_LENGTHS = sp.symbols( "L_0 L_1 L_2" )
    NON_UNIFORM_POTENTIALS = sp.symbols( "V_0 V_1 V_2" )
    DEFAULT_START = 0
    
    def default_non_uniform_length_potential_table(): 
        return { 
                    StairWell.NON_UNIFORM_STAIR_LENGTHS[ ii ] : StairWell.NON_UNIFORM_POTENTIALS[ ii ] 
                    for ii in range( len( StairWell.NON_UNIFORM_POTENTIALS ) ) 
            }
    
    def default_uniform_length_potential_table(): 
        return { 
                    StairWell.UNIFORM_STAIR_LENGTHS[ ii ] : StairWell.UNIFORM_POTENTIALS[ ii ] 
                    for ii in range( len( StairWell.UNIFORM_POTENTIALS ) ) 
            }

    @classmethod
    def eval( 
                cls, 
                position, 
                start = DEFAULT_START, 
                potentials = NON_UNIFORM_POTENTIALS, 
                lengths = NON_UNIFORM_STAIR_LENGTHS#, 
                #assumptions = DEFAULT_ASSUMPTIONS 
            ): 
        position = position + start
        if position < lengths[ 0 ]: 
            return potentials[ 0 ]
        elif position < ( lengths[ 0 ] + lengths[ 1 ] ): 
            return potentials[ 1 ]
        elif position < ( lengths[ 0 ] + lengths[ 1 ] + lengths[ 2 ] ): 
            return potentials[ 2 ]

def zip_to_table( keys, values ): 
    assert len( keys ) == len( values )
    keys = list( keys )
    values = list( values )
    return { keys[ ii ] : values[ ii ] for ii in range( len( keys ) ) }

def table_to_pairs( table ): 
    keys = list( table.keys() )
    values = list( table.values() )
    return [ ( keys[ ii ], values[ ii ] ) for ii in range( len( keys ) ) ]

make_psi_parameter_constrained = lambda psi_function, region_potential_table, position : \
        [ psi_function( position < region ) for region in region_potential_table.keys() ]

make_numbered_psi_function = lambda psi_function, region_potential_table : [ \
        sp.Function( '\\' + str( psi_function ) + "_{" + str( ii ) + '}' ) \
        for ii in range( len( region_potential_table ) ) \
    ]

make_psi_numbered = lambda psi_function, region_potential_table, position : [ \
        psi( position ) for psi in make_numbered_psi_function( psi_function, region_potential_table ) \
    ]

def make_psi_numbered_parameter_constrained( psi_function, region_potential_table, position ): 
    psis = make_numbered_psi_function( psi_function, region_potential_table )
    regions = region_potential_table.keys()
    return [ psis[ ii ]( position < regions[ ii ] ) for ii in range( len( region_potential_table ) ) ]

potential_none_to_list = lambda none_canidate : [] if none_canidate == None else none_canidate

class Boundries: 
    """TODO: (Speculative)
        * : Add relations between objects in boundry, such as =, >, <, <=, >=, and, or, xor
        * : Make no "special" group, but make it be able to have groups of groups of groups for ex.
        * : More granular remove_boundries, possibly that can work with boundries_with
        * : Somehow make boundries associative/communative <- sortof accomplished using append_boundries 
                and update_all_boundry_conditions*
    """
    
    BOUNDRY_ALL = "LastUpdatedAllBoundryConditions"
    BOUNDRY_QUERY_RESPONCE = "LastBoundryWithQueryResponce"
    
    def __init__( self, initial_boundries = None ): 
        self.boundries = not_none_value( initial_boundries, {} )
    
    def add_boundries( self, set_name, boundries, automatically_append = False, append_override = False ): 
        set_name_in_boundries = set_name in self.boundries
        """Prevents overwriting boundries unless explicitly specified to do so.
        It is computed twice, but if the assertion is thrown, the client may see 
        the explicit problem."""
        assert True if automatically_append == True else not set_name_in_boundries, """
                Attempt to set boundries when set already exists, set `automatically_append` 
                to `True` or call `append_boundries` to append
                """
        if set_name_in_boundries == True and automatically_append == True: 
            self.append_boundries( set_name, boundries, append_override )
        elif set_name_in_boundries == False: 
            self.boundries[ set_name ] = boundries
            setattr( self, set_name, self.boundries[ set_name ] )
        else: 
            assert set_name_in_boundries, "Attempt to overwrite existing boundries: " + set_name
        return set_name, self.boundries[ set_name ]
    
    def append_boundries( self, set_name, to_append, override = False ): 
            boundries = self.boundries[ set_name ]
            to_append_keys = tuple( to_append )
            for key in to_append_keys: 
                value = to_append[ key ]
                if key in boundries: 
                    if value == boundries[ key ]: 
                        continue
                    elif not ( value in boundries ): 
                        boundries[ value ] = key
                    elif override: 
                        boundries[ key ] = value
                    else: 
                        assert key in boundries and ( not ( value in boundries ) ) and override
                else: 
                        boundries[ key ] = value
            return set_name, boundries

    def combind_boundry_conditions( self, first_set, second_set, new_name = None, allow_update = False, allow_reset = False ): 
        first_set_is_string = type( first_set ) is str
        second_set_is_string = type( second_set ) is str
        passed_boundry_set = not ( first_set_is_string or second_set_is_string )
        assert passed_boundry_set if new_name == None else True, """
        If passing a boundry set, not the name of the boundry set, please specify a name of the resulting boundry_set
        """
        name = new_name if passed_boundry_set else new_name if new_name != None else first_set + second_set
        name_in_boundries = name in self.boundries
        assert name_in_boundries or new_name or allow_update or allow_reset, """
        Name already in boundry set, either specify 
        `True` for `allow_update` or `allow_reset` or specify new name
        """
        if not name_in_boundries or ( allow_reset and name_in_boundries ): 
            self.boundries[ name ] = {}
        assert not ( name_in_boundries and not allow_update ), """
        About to update boundry, when no update is allowed, to allow updates, please specify `allow_update` as `True`
        """
        self.append_boundries( name, self.boundries[ first_set ] if first_set_is_string else first_set ), "first set", self.boundries[ first_set ]
        return self.append_boundries( name, self.boundries[ second_set ] if second_set_is_string else second_set )
    
    def update_all_boundry_conditions( self, boundry_all_name = BOUNDRY_ALL, return_old = False ): 
        old = {}
        if boundry_all_name in self.boundries: 
            old = self.boundries.pop( boundry_all_name )
        boundry_keys = tuple( self.boundries.keys() )
        self.boundries[ boundry_all_name ] = {}
        for key in boundry_keys: 
            if key != boundry_all_name: 
                self.combind_boundry_conditions( boundry_all_name, key, boundry_all_name, True, False )
        return self.boundries[ boundry_all_name ]
    
    def remove_boundry_set( self, set_name ): 
        return set_name, self.boundries.pop( set_name )
    
    def remove_boundries( 
                self, 
                set_name, 
                keys : list, 
                values : list, 
                key_or_value : list 
            ): 
        removed = []
        boundry_set = self.boundries[ set_name ]
        keys = tuple( potential_none_to_list( keys ) + potential_none_to_list( key_or_value ) )
        removed = [ boundry_set.pop( key ) for key in keys ]
        values = tuple( potential_none_to_list( values ) + potential_none_to_list( key_or_value ) )
        removed = removed + [ boundry_set[ key ] for key in boundry_set.keys() if boundry_set[ key ] in values ]
        return set_name, removed
    
    def has_set( self, set_name ): 
        return set_name in self.boundries
    
    def display( self ): 
        for boundry_set in self.boundries: 
            display( boundry_set )
            for boundry in self.boundries[ boundry_set ]: 
                display( sp.Eq( boundry, self.boundries[ boundry_set ][ boundry ] ) )
    
    def boundries_with_in_set( self, set_name, query ): 
        boundry_set = self.boundries[ set_name ]
        result = {}
        for key in boundry_set: 
            value = boundry_set[ key ]
            if key.has( query ) or value.has( query ): 
                result[ key ] = value
        return result
    
    def boundries_with( self, query, query_name = BOUNDRY_QUERY_RESPONCE ): 
        self.update_all_boundry_conditions( query_name )
        return self.boundries_with_in_set( query_name, query )
                

to_functions = lambda functions_with_parameters : tuple( function for function in functions_with_parameters )

class TimeIndependentSchrodingerConstantPotentials1D( Symbols ): 

    DEFAULT_CHECK_POINT_NAME_BASE = "TimeIndependentSchrodingerConstantPotentials1DCheckPoint"
    DEFAULT_CONSTANT_NAME_BASE = 'k'
    
    CHECK_POINT_BEFORE_SOLVE_HARMONIC_CONSTANT = "BeforeSolveHarmonicConstant"
    CHECK_POINT_SOLVED_HARMONIC_CONSTANT = "SolveHarmonicConstantSolved"
    CHECK_POINT_SUBSTITUTE_HARMONIC_CONSTANT = "SubstitutingHarmonicConstant"
    CHECK_POINT_HARMONIC_SOLUTION_TO_CANONOCAL_FORM = "HarmonicSolutionToCanonicalForm"

    BOUNDRY_CONTINUITY_CONDITIONS = "ContinuityConditions"
    BOUNDRY_REPEATING_POTENTIALS_CONDITION = "RepeatingPotentialsCondition"
    BOUNDRY_ALL = "LastUpdatedAllBoundryConditions"
    
    def __init__( 
                self, 
                region_potential_table, 
                region_end = None, 
                region_start = None, 
                initial_boundries = None, 
                repeating = False, 
                inverse_repeating = False, 
                psi_function = PSI_FUNCTION, 
                potential_function = POTENTIAL_FUNCTION, 
                total_energy = TOTAL_ENERGY_SYMBOL, 
                mass = MASS_SYMBOL, 
                reduced_planck_constant = hbar, 
                position = POSITION_SYMBOL, 
                make_psis = make_psi_numbered, 
                check_point_name_base = DEFAULT_CHECK_POINT_NAME_BASE, 
                constant_name_base = DEFAULT_CONSTANT_NAME_BASE, 
                check_point_count= 0, 
                psi_parameter_based = None
            ): 
        self.region_potential_table = region_potential_table
        self.region_start = not_none_value( region_start, 0 )
        self.region_end = not_none_value( region_end, tuple( region_potential_table.keys() )[ -1 ] )
        self.repeating = repeating
        self.inverse_repeating = inverse_repeating 
        self.psi_function = psi_function 
        self.potential_function = potential_function 
        self.total_energy = total_energy 
        self.mass = mass 
        self.reduced_planck_constant = reduced_planck_constant 
        self.position = position
        self.make_psis = make_psis
        self.check_point_name_base = check_point_name_base
        self.constant_name_base = constant_name_base
        self.check_point_count = check_point_count
        self.psi_parameter_based = not_none_value( psi_parameter_based, self.make_psis == make_psi_parameter_constrained )
        self.psis = self.make_psis( self.psi_function, self.region_potential_table, self.position )
        self.boundries = Boundries( initial_boundries )
        region_psi_table = self.region_psi_table()        
        self.vanilla_schrodinger_equation_1d = \
                Stepper( time_independent_schroedinger_equation_1d( 
                        self.psi_function, 
                        self.potential_function, 
                        self.total_energy, 
                        self.mass, 
                        self.reduced_planck_constant, 
                        self.position
                    ) )
        self.equations = [
                Stepper( self.vanilla_schrodinger_equation_1d.last_step() \
                        .subs( self.potential_function( self.position ), potential ) \
                        .replace( self.psi_function( self.position ), region_psi_table[ region ] ) ) \
                for region, potential in self.region_potentials()
            ]
        for psi in self.psis: 
            self.add_symbol( psi )
        self.harmonic_constants = self._make_harmonic_constants()
        self._impose_continuity_conditions()
        if repeating == True: 
            self.impose_repeating_potentials_condition()
    
    def regions( self ): 
        return tuple( self.region_potential_table.keys() )
    
    def potentials( self ): 
        return ( self.region_potential_table[ region ] for region in self.region_potential_table )
    
    def region_potentials( self ): 
        return table_to_pairs( self.region_potential_table )
    
    def region_psi_table( self ): 
        return zip_to_table( self.region_potential_table.keys(), self.psis )
    
    def second_derivative( self, equation_index : int ): 
        return sp.Derivative( self.psis[ equation_index ], ( self.position, 2 ) )

    def _new_check_point_number( self ): 
        self.check_point_count += 1
        return str( self.check_point_count - 1 )
        
    def _harmonic_constant_name( self, equation_index, name_base = None ): 
        name_base = not_none_value( name_base, self.constant_name_base )
        return name_base + '_' + str( equation_index )
    
    def _make_harmonic_constant( self, equation_index : int, name_base = None, restore_before_checkpoint = False ): 
        equation = self.equations[ equation_index ]
        psi = self.psis[ equation_index ]
        before_check_point = self.check_point_name_base \
                + TimeIndependentSchrodingerConstantPotentials1D.CHECK_POINT_BEFORE_SOLVE_HARMONIC_CONSTANT \
                + self._new_check_point_number()
        equation.check_point( before_check_point )
        psi_solution = sp.solve( equation.last_step(), psi )
        psi_solution = psi_solution[ 0 ] if type( psi_solution ) is list else psi_solution
        equation.add_step( sp.Eq( psi, psi_solution ) )
        second_deriviative = self.second_derivative( equation_index )
        # For Stepper's / and ** are the same as /= **=
        equation /= second_deriviative
        equation **= ( -1 )
        equation.root( 2 )
        constant_name = self._harmonic_constant_name( equation_index, name_base )
        equation.right_to_constant( constant_name )
        equation.check_point( 
                self.check_point_name_base \
                    + TimeIndependentSchrodingerConstantPotentials1D.CHECK_POINT_SOLVED_HARMONIC_CONSTANT \
                    + self._new_check_point_number()
            )
        equation.substitute_constant( equation.constants_as_symbols().symbol_by_string_name( constant_name ) )
        equation.check_point( 
                self.check_point_name_base \
                + TimeIndependentSchrodingerConstantPotentials1D.CHECK_POINT_SUBSTITUTE_HARMONIC_CONSTANT \
                + self._new_check_point_number()
            )
        equation **= 2
        equation *= psi
        equation -= equation.right()
        equation.check_point( 
                self.check_point_name_base \
                + TimeIndependentSchrodingerConstantPotentials1D.CHECK_POINT_HARMONIC_SOLUTION_TO_CANONOCAL_FORM \
                + self._new_check_point_number()
            )
        if restore_before_checkpoint: 
            equation.restore_from_check_point( before_check_point, True )
        return equation.constant_symbols().symbol_by_string_name( constant_name )
    
    def _make_harmonic_constants( self, name_base = None ): 
        return [ self._make_harmonic_constant( ii, name_base ) for ii in range( len( self.region_potential_table ) ) ]
    
    def _impose_continuity_conditions( self, parameter_based = None ): 
        """Run automatically in __init__ constructor, standard requirment of Quantum mechanichs where the 
        wave function must be continuous, realized here by the symbolic representations of what is 
        (hopefully) functionally equivelent too: 
        let there be a wave functions psi indexed by i, with corresponding distances D indexed by i
        let \psi_{i}( L ) = \psi_{i + 1}( L ) where L = \sum_0^i{D_i}
        This will be imposed for every wave function in the set that has a wave function following it
        this is non-circular, see `impose_repeating_potentials_condition` for making 
        a repeating condition
        
        return: name of "boundry set" (str) added and boundry set (dict)
        rtype: tuple( str, dict )
        """
        assert not not_none_value( self.psi_parameter_based, parameter_based ), """
        Parameter based continuity condition not yet supported! Try using numbered instead (default)
        TODO: Requires using infentesmials
        """
        regions = tuple( self.region_psi_table().keys() )
        assert len( self.psis ) == len( regions )
        length = len( self.psis )
        return self.boundries.add_boundries( 
                TimeIndependentSchrodingerConstantPotentials1D.BOUNDRY_CONTINUITY_CONDITIONS, {
                        self.psis[ ii ].func( regions[ ii ] ) : self.psis[ ii + 1 ].func( regions[ ii ] )
                                for ii in range( length ) if ( ii + 1 ) < length
            } )

    def update_harmonic_constants( self, name_base = None ): 
        self.harmonic_constants = self._make_harmonic_constants( name_base )
        return self.harmonic_constants
    
    def psis_to_functions( self ): 
        return to_functions( self.psis )
    
    def impose_repeating_potentials_condition( self, start = None, end = None ): 
        """Impose the assumption that the first wave function 
        of the first (zeroth/0th) region at `start` will 
        be equal to the last ("nth"/"n'th") wave function 
        at `end`, `start` defaults to `self.region_start`, 
        and `end` to `self.region_end`
        
        Arguments: 
        
        start: The parameter to the first/0th/zeroth wave function, 
                physical location of the beggining of the first potential 
                region, defaults to `self.region_start`, the zeroth 
                wave function of this parameter will be set to the nth/last 
                wave function of `end`
        end: The parameter to the last/nth wave function and the physical 
                location of the end of the last potential region, defaults 
                to `self.region_end`. the last/nth wave function of this 
                parameter will be set to the first/0th/zeroth wave function 
                of `end`
        return: name of "boundry set" (str) added and boundry set (dict)
        rtype: tuple( str, dict )
        """
        start = not_none_value( start, self.region_start )
        end = not_none_value( end, self.region_end )
        psis = self.psis_to_functions() 
        return self.boundries.add_boundries( 
                TimeIndependentSchrodingerConstantPotentials1D.BOUNDRY_REPEATING_POTENTIALS_CONDITION, { 
                        psis[ 0 ].func( start ) : psis[ -1 ].func( end ) 
            } )
    