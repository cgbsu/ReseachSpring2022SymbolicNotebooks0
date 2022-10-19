import sympy as sp
import sympy.physics.units.quantities as sq
from sympy.physics.quantum.constants import hbar
import copy
from collections import OrderedDict

PSI_FUNCTION = sp.Function("psi")
POTENTIAL_FUNCTION = sp.Function("V")
TOTAL_ENERGY_SYMBOL = sq.Symbol('E_{total}', nonzero = True, real = True, positive = True)
MASS_SYMBOL = sq.Symbol('m', positive = True, nonzero = True)
POSITION_SYMBOL = sp.Symbol('x', positive = True)
DEFAULT_CONJUGATE_NOT_SQUARED_ABSOLUTE_VALUE = True
DEFAULT_NORMALIZATION_VALUE = 1
INDEFINITE_NORMALIZATION_INTEGRAL = None
DEFAULT_CONJUGATE_NOT_SQUARED_ABSOLUTE_VALUE = True

def makeDistance(region): 
    return sp.Symbol(f'L_{region}', real = True, finite = True)

def makeStartDistance(region): 
    return sp.Symbol(f'L_{region - 1}', positive = True, real = True)

def makeFromToSymbol(baseName, index): 
    return {
            "next" : sp.Symbol(f"{baseName}_{index}_{index + 1}"), 
            "previous" : sp.Symbol(f"{baseName}_{index}_{index - 1}")
        }

class RegionCoefficients: 
    def __init__(self, transmissionCoefficent, reflectionCoefficient): 
        self.transmissionCoefficent = transmissionCoefficent
        self.reflectionCoefficient = reflectionCoefficient

def isIdentifier(identifier):
    firstCharacter = ord(identifier[0])
    traditionalIdentifier = (firstCharacter >= ord('a') and firstCharacter >= ord('Z')) or firstCharacter == ord('_')
    if identifier.startswith("conjugate"):
        return False
    return traditionalIdentifier

def functionNameFromIdentifier(identifier): 
    return identifier + "Function"

def orderNames(names, sortIndex = 0): 
    sameStart = {}
    results = []
    for name in names: 
        if sortIndex < len(name): 
            sortCharacter = name[sortIndex]
            if sortCharacter in sameStart.keys(): 
                sameStart[sortCharacter].append(name)
            else: 
                sameStart[sortCharacter] = [name]
        else: 
            results.append(name)
    for ordered in [orderNames(sameStart[character], sortIndex + 1) for character in sorted(list(sameStart))]: 
        results += ordered
    return results 

def symbolicToIdentifier(symbolic):
    identifier = str(symbolic)
    replacementList = {
            '{' : "OCB", 
            '}' : "CCB", 
            '(' : "OP", 
            ')' : "CP", 
            '[' : "OSB", 
            ']' : "CSB", 
            '-' : "N", 
            "Backslash" : "\\"
        }
    for toReplace, replacement in replacementList.items(): 
        identifier = identifier.replace(toReplace, replacement)
    return identifier

def substituteIdentifierAtomsList(symbolic):
    substitutionList = {}
    atoms = symbolic.atoms()
    atoms |= symbolic.atoms(sp.Function)
    for atom in atoms: 
        if isIdentifier(str(atom)) == True: 
            substitutionList[atom] = symbolicToIdentifier(atom)
    return substitutionList

def substituteIdentifierAtoms(symbolic):
    return symbolic.subs(substituteIdentifierAtomsList(symbolic))

def makeBoundrySymbol(regionIndex : int): 
    return sp.Symbol(f'B_{regionIndex}')

class RegionSymbols: 
    def __init__(self, regionIndex): 
        self.regionIndex = regionIndex
        self.waveFunction = sp.Function(f'psi_{self.regionIndex}')
        self.constants = [
                sp.Symbol('C_{{' + str(self.regionIndex) + '}_t}'), 
                sp.Symbol('C_{{' + str(self.regionIndex) + '}_r}')
            ]
        self.distance = makeDistance(self.regionIndex)
        self.harmonicConstant = sp.Symbol(f'k_{self.regionIndex}', real = True)
        self.boundry = makeBoundrySymbol(self.regionIndex)
        self.nextBoundry = makeBoundrySymbol(self.regionIndex + 1)
        self.normalizationConstant = sp.Symbol(f'N_{self.regionIndex}')
        self.partSummeries = [
                sp.Function(f'psi_{str(self.regionIndex)}_t'), 
                sp.Function(f'psi_{str(self.regionIndex)}_r')
            ]
        self.mass = MASS_SYMBOL
        self.constantPotential = sp.Symbol(f'V_{self.regionIndex}', positive = True, real = True)
        self.startDistance = makeStartDistance(self.regionIndex)
        self.transmissionCoefficents = makeFromToSymbol("T", self.regionIndex)
        self.reflectionCoefficents = makeFromToSymbol("R", self.regionIndex)
        self.next = RegionCoefficients(self.transmissionCoefficents["next"], self.reflectionCoefficents["next"])
        self.previous = RegionCoefficients(self.transmissionCoefficents["previous"], self.reflectionCoefficents["previous"])

def makeCoefficents(first, second): 
    transmission = (sp.Abs(second.constants[0]) ** 2) / (sp.Abs(first.constants[0]) ** 2)
    reflection = (sp.Abs(first.constants[1]) ** 2) / (sp.Abs(first.constants[0]) ** 2)
    return RegionCoefficients(transmission, reflection)

def makeCoefficentsFromHarmonicConstants(first, second): 
    transmission = 2 * first.harmonicConstant / (first.harmonicConstant + second.harmonicConstant)
    reflection =  (first.harmonicConstant - second.harmonicConstant) / (first.harmonicConstant + second.harmonicConstant)
    return RegionCoefficients(transmission, reflection)

def removeAbsAndConjugate(toConjugate): 
    wild = sp.Wild('wild')
    return toConjugate.replace(sp.Abs(wild), sp.conjugate(wild))

def removeAbs(toRemoveFrom): 
    wild = sp.Wild('wild')
    return toRemoveFrom.replace(sp.Abs(wild), wild)

def ratioFromNormalizeRatio(ratio): 
    noAbs = removeAbs(ratio)
    return ratio, sp.conjugate(ratio)

def makeScatteringMatrix(from_, to, coefficents : RegionCoefficients = None): 
    ratios = coefficents if coefficents else (from_.previous if from_.regionIndex > to.regionIndex else from_.next)
    transmission, transmissionConjugate = ratioFromNormalizeRatio(ratios.transmissionCoefficent)
    reflection, reflectionConjugate = ratioFromNormalizeRatio(ratios.reflectionCoefficient)
    return {
            "inputs" : [symbolicToIdentifier(ratios.transmissionCoefficent), symbolicToIdentifier(ratios.reflectionCoefficient)], 
            "scatteringMatrix" : sp.Matrix([
                    [sp.sqrt(reflectionConjugate), sp.sqrt(transmission)], 
                    [sp.sqrt(transmissionConjugate), sp.sqrt(reflection)]
                ])
        }

def makeTransferMatrix(scatteringMatrix_): 
    scatteringMatrix = scatteringMatrix_["scatteringMatrix"]
    scatteringMatrix_["transferMatrix"] = sp.Matrix([
            [
                    scatteringMatrix.col(1).row(0) - (scatteringMatrix.col(1).row(1) 
                            * (scatteringMatrix.col(0).row(0)) * (scatteringMatrix.col(0).row(1) ** (-1))), 
                    scatteringMatrix.col(1).row(1) * (scatteringMatrix.col(0).row(1) ** (-1))
            ], 
            [
                    -scatteringMatrix.col(0).row(0) * (scatteringMatrix.col(0).row(1) ** (-1)), 
                    scatteringMatrix.col(0).row(1) ** (-1)
            ]
        ])
    return scatteringMatrix_

def makeBarrierMatrix(from_ : RegionSymbols): 
    transmission = from_.partSummeries[0](from_.startDistance)
    reflection = from_.partSummeries[1](from_.startDistance)
    return {
            "inputs" : [symbolicToIdentifier(transmission), symbolicToIdentifier(reflection)], 
            "matrix" : sp.Matrix([
                    [transmission], 
                    [reflection]
                ])
        }

def transferWithHarmonicConstants(from_, to): 
    transmission, reflection = makeCoefficentsFromHarmonicConstants(from_, to)
    scatteringMatrix = makeScatteringMatrix(transmission, reflection)
    return generalTransferFromScatteringMatrix(from_, to, scatteringMatrix)

def generalTransfer(from_, to): 
    return generalTransferFromScatteringMatrix(from_, to, makeScatteringMatrix(from_, to))

def generalTransferFromScatteringMatrix(from_, to, scatteringMatrix): 
    transferMatrix = makeTransferMatrix(scatteringMatrix)
    input_ = makeBarrierMatrix(to)
    result = makeBarrierMatrix(from_)
    transferMatrix["inputs"] += result["inputs"]
    transferMatrix["outputs"] = input_["inputs"]
    return {
            "from" : from_, 
            "to" : to, 
            "matricies" : transferMatrix, 
            "transfer" : sp.Eq(input_["matrix"], transferMatrix["transferMatrix"] * result["matrix"])
        }

def lambdifyTransfer(transferData): 
    parameters = transferData["matricies"]["inputs"]
    outputs = transferData["matricies"]["outputs"]
    calculation = transferData["transfer"].rhs
    result = transferData["transfer"].lhs
    transferData["functionData"] = { 
            "paramters" : parameters, 
            "functions" : {
                    functionNameFromIdentifier(outputs[0]) : sp.lambdify(parameters, substituteIdentifierAtoms(calculation.row(0)[0])), 
                    functionNameFromIdentifier(outputs[1]) : sp.lambdify(parameters, substituteIdentifierAtoms(calculation.row(1)[0]))
                }
        }
    return transferData

def inputCoefficients(functions, inputs, coefficients): 
    assert len(functions) == 2, ("Wrong number of of functions to predict the wave function (reflective and transmission)"
                                + "at a certain coordinate, are you using more than 2 dimensions?")
    satisfiedArguments, waveFunctionInputs = satisfyParameterDict(inputs, coefficients).values()
    assert len(waveFunctionInputs) == 2, "Insufficiant arguemnts for coefficents"
    return satisfiedArguments, waveFunctionInputs

def performTransfersImplementation(transfers : list[dict], previousTransferValues, transferValues, coefficients : dict): 
    functionData = transfers[0]['functionData']
    inputs = transfers[0]['matricies']['inputs']
    outputs = transfers[0]['matricies']['outputs']
    functions = functionData['functions']
    satisfiedArguments, waveFunctionInputs = inputCoefficients(functions, inputs, coefficients[0])
    arguments, remainingArguments = satisfyParameterDict(waveFunctionInputs, previousTransferValues).values()
    assert len(remainingArguments) == 0, "Parameter not satisfied!"
    arguments = tuple(satisfiedArguments.values()) + tuple(arguments.values())
    waveFunctions = tuple(functions.keys())
    transferValues |= previousTransferValues
    thisTransferValues = {
            outputs[0] : functions[waveFunctions[0]](*arguments), 
            outputs[1] : functions[waveFunctions[1]](*arguments)
        }
    if len(transfers) <= 1:
        return transferValues | thisTransferValues
    else: 
        return performTransfersImplementation(
                transfers[1:], 
                thisTransferValues, 
                transferValues, 
                coefficients[1:]
            )


def performTransfers(transfers : list[dict], initialTransmission, initialReflection, coefficients : dict): 
    functions = transfers[0]['functionData']['functions']
    inputs = transfers[0]['matricies']['inputs']
    satisfiedArguments, waveFunctionInputs = inputCoefficients(functions, inputs, coefficients[0])
    return performTransfersImplementation(
            transfers, 
            {
                    waveFunctionInputs[0] : initialTransmission, 
                    waveFunctionInputs[1] : initialReflection
            }, 
            {}, 
            coefficients
        )

def satisfyParameterDict(parameters, inputMapping): 
    arguments = {}
    isMappingType = type(inputMapping) is dict or type(inputMapping) is OrderedDict
    assert isMappingType, "inputMapping is not of type dict, need to map names of paramters to values"
    for parameter, argument in inputMapping.items(): 
        satisfied = parameter == parameters[0]
        parameters = parameters[1:]
        if satisfied == False: 
            print(parameter)
            assert satisfied, ("satisfyParameters: Parameter not in parameter list or is not"
                    "the current parameter (parameter order must be preserved)!")
        else: 
            arguments[parameter] = argument
    return {"arguments" : arguments, "remainingParameters" : parameters}

def generateGeneralTransferFunctions(numberOfRegions): 
    transferFunctionData = {"regionSymbols" : [RegionSymbols(ii - 1) for ii in range(numberOfRegions + 2)]}
    regionSymbols = transferFunctionData["regionSymbols"]
    transferFunctionData["transfers"] = [
            generalTransfer(regionSymbols[ii + 1], regionSymbols[ii]) \
            for ii in range(1, len(regionSymbols) - 1)
        ]
    transferFunctionData["transferFunctions"] = [
            lambdifyTransfer(transfer) for transfer in transferFunctionData["transfers"]
        ]
    return transferFunctionData

def constantPotentialTimeIndependentSchroedingerEquation1D( 
            regionSymbols : RegionSymbols, 
            totalEnergy = TOTAL_ENERGY_SYMBOL, 
            reducedPlanckConstant = hbar, 
            position = POSITION_SYMBOL 
        ): 
    return sp.Eq( 
            ( ( -( reducedPlanckConstant ** 2 ) / ( 2 * regionSymbols.mass ) ) \
                    * sp.Derivative(regionSymbols.waveFunction(position), (position, 2)))
                    + (regionSymbols.constantPotential * regionSymbols.waveFunction(position)), 
            totalEnergy * regionSymbols.waveFunction(position)
        )

def simpleWaveFunctionNormalization( 
            from_, toOrIndefinite, 
            regionSymbols : RegionSymbols, 
            position = POSITION_SYMBOL, 
            conjugateNotSquaredAbsoluteValue 
                    = DEFAULT_CONJUGATE_NOT_SQUARED_ABSOLUTE_VALUE 
        ): 
    integralFunction = regionSymbols.waveFunction(position) * sp.conjugate(regionSymbols.waveFunction(position)) \
            if conjugateNotSquaredAbsoluteValue \
            else sp.Abs(regionSymbols.waveFunction(position)) ** 2
    if toOrIndefinite: 
        return sp.Eq(
                sp.Integral(
                        integralFunction, 
                        (position, from_, toOrIndefinite)
                    ),
                regionSymbols.normalizationConstant
            )
    else:
        return sp.Eq(
                sp.Integral(integralFunction), 
                regionSymbols.normalizationConstant
            )

def manipulate(equation, operation): 
    return sp.Eq(operation(equation.lhs), operation(equation.rhs))

def secondDerivative(regionSymbols : RegionSymbols, position = POSITION_SYMBOL): 
    return sp.Derivative(regionSymbols.waveFunction(position), (position, 2))

def constantFactor(
            regionSymbols : RegionSymbols, 
            mass = MASS_SYMBOL, 
            reducedPlanckConstant = hbar
        ):
    return (reducedPlanckConstant ** 2) / (2 * mass)

def secondDerivativeTerm(
            regionSymbols : RegionSymbols, 
            position = POSITION_SYMBOL, 
            mass = MASS_SYMBOL, 
            reducedPlanckConstant = hbar
        ):
    return constantFactor(regionSymbols) * secondDerivative(regionSymbols)

def extractHarmonicConstant(regionSymbols, equation): 
    waveFunction = regionSymbols.waveFunction(POSITION_SYMBOL)
    solveForWaveFunction = sp.Eq(waveFunction, sp.solve(equation, regionSymbols.waveFunction(POSITION_SYMBOL))[0])
    return sp.Eq(
            regionSymbols.harmonicConstant, 
            manipulate(solveForWaveFunction, lambda step : sp.sqrt((step / secondDerivative(regionSymbols)) ** (-1))).refine().rhs
        )


def extractAmplitudeCoefficents(exponentialEquation, position = POSITION_SYMBOL): 
    C0 = sp.Wild("C0")
    C1 = sp.Wild("C1")
    harmonic = sp.Wild("k")
    results = exponentialEquation.match(C0 * sp.exp(harmonic * position) + C1 * sp.exp(-harmonic * position))
    
    return {
            "transmission" : results[C0], 
            "reflection" : results[C1], 
            "harmonicConstant" : results[harmonic]
    }

def createGeneralSolution(regionSymbols : RegionSymbols, waveEquation : sp.Eq, normalization : sp.Eq): 
    boundries = {
        regionSymbols.waveFunction(regionSymbols.startDistance) : regionSymbols.boundry, 
        regionSymbols.waveFunction(regionSymbols.distance) : regionSymbols.nextBoundry
    }
    harmonicConstant = extractHarmonicConstant(regionSymbols, waveEquation)
    generalSolution = sp.dsolve(waveEquation, ics = boundries)
    generalSolution = generalSolution.subs({harmonicConstant.rhs : harmonicConstant.lhs})
    return {
            "boundries" : boundries, 
            "harmonicConstantEquation" : harmonicConstant, 
            "generalSolution" : generalSolution
        }

def solveUnconstrainedParticularSolution(regionSymbols, generalSolution : sp.Eq): 
    amplitudes = extractAmplitudeCoefficents(generalSolution["generalSolution"].rhs, POSITION_SYMBOL)
    exponential = generalSolution["generalSolution"].subs({
        amplitudes["transmission"] : regionSymbols.constants[0], 
        amplitudes["reflection"] : regionSymbols.constants[1]
    })
    return {
            "generalSolution" : generalSolution, 
            "exponential" : exponential, 
            "amplitudes" : amplitudes
        }

## TODO: ##


def extractNonZero(symbolic):
    harmonic = sp.Wild('k')
    expression = sp.Wild('C')
    nonZero = sp.Ne(harmonic, 0)
    otherExpression = sp.Wild('A')
    otherCondition = sp.Wild('B')
    otherStuff = sp.Wild('Q')
    extracted = symbolic.match(otherStuff + sp.Piecewise((expression, nonZero), (otherExpression, otherCondition)))
    return {
            "nonZero" : extracted[expression], 
            "otherwise" : extracted[otherExpression], 
            "rest" : extracted[otherStuff]
        }

## TODO: ##

def solveForConstrainedAmplitudeCoefficients(
        regionSymbols : RegionSymbols, 
        normalization, 
        unconstrainedParticularSolution : dict
    ): 
    integration = normalization.subs({
            regionSymbols.waveFunction(POSITION_SYMBOL) \
                    : unconstrainedParticularSolution["exponential"].rhs
        }).doit()
    extractedConditions = extractNonZero(integration.lhs)
    nonZeroNormalizationCase = sp.Eq(
            extractedConditions["rest"] + extractedConditions["nonZero"], 
            integration.rhs
        )
    c0Solutions = sp.solve(nonZeroNormalizationCase,  regionSymbols.constants[0])
    c1Solutions = sp.solve(nonZeroNormalizationCase, regionSymbols.constants[1])
    unconstrainedParticularSolution["unconstrainedAmplitudes"] = {
            "transmission" : c0Solutions, 
            "reflection" : c1Solutions
        }
    c0Equation = sp.Eq(
            unconstrainedParticularSolution["amplitudes"]["transmission"] \
                    * unconstrainedParticularSolution["amplitudes"]["transmission"], 
            (c0Solutions[0] * c0Solutions[1]).simplify()
        )
    constrainedC1Solutions = sp.solve(c0Equation, regionSymbols.constants[1])
    c1ConstrainedSolution = sp.Eq(
            regionSymbols.constants[1] ** 2, 
            (constrainedC1Solutions[0] * constrainedC1Solutions[1]).simplify().refine()
        )
    c1Equation = sp.Eq(
            unconstrainedParticularSolution["amplitudes"]["reflection"] \
                    * unconstrainedParticularSolution["amplitudes"]["reflection"], 
            (c1Solutions[0] * c1Solutions[1]).simplify()
        )
    constrainedC0Solutions = sp.solve(c1Equation, regionSymbols.constants[0])
    c0ConstrainedSolution = sp.Eq(
            regionSymbols.constants[0] ** 2, 
            (constrainedC0Solutions[0] \
                    * constrainedC0Solutions[1]).simplify().refine()
        )
    unconstrainedParticularSolution["amplitudeEquations"] = {
            "transmission" : c0Equation, 
            "reflection" : c1Equation
        }
    unconstrainedParticularSolution["amplitudeConstrainedSolutions"] = {
            "transmission" : constrainedC0Solutions, 
            "reflection" : constrainedC1Solutions
        }
    unconstrainedParticularSolution["amplitudeConstrainedSolution"] = {
            "transmission" : c0ConstrainedSolution, 
            "reflection" : c1ConstrainedSolution
        }
    unconstrainedParticularSolution["expandedExponential"] \
            = (unconstrainedParticularSolution["exponential"].rhs \
                    * sp.conjugate(unconstrainedParticularSolution["exponential"].rhs)
              ).expand()
    return unconstrainedParticularSolution
