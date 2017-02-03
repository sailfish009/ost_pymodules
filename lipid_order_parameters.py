#------------------------------------------------------------------------------------------------
#This file is part of the ost_pymodules project (https://github.com/njohner/ost_pymodules).
#
#Copyright 2015 Niklaus Johner
#
#ost_pymodules is free software: you can redistribute it and/or modify
#it under the terms of the GNU Lesser General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#ost_pymodules is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU Lesser General Public License for more details.
#
#You should have received a copy of the GNU Lesser General Public License
#along with ost_pymodules.  If not, see <http://www.gnu.org/licenses/>.
#------------------------------------------------------------------------------------------------
"""
.. codeauthor:: Niklaus Johner <niklaus.johner@a3.epfl.ch>

This module contains functions to calculate lipid order parameters.
"""

try:
  from ost import *
  import time
  import numpy as npy
  import os,math
  import entity_alg,trajectory_utilities,surface_alg,file_utilities
except:
  print 'could not import at least one of the modules nedded: ost, time, numpy, os, math, entity_alg,trajectory_utilities,surface_alg,file_utilities'


__all__=['AnalyzeMolecularOrderParameters',"CalculateMolecularOrderParameters"]

def _MolecularOrderParameter(v1,v2):
  a=geom.Angle(v1,v2)
  return 0.5*(3.*math.cos(a)**2.0-1)

def CalculateMolecularOrderParameter(res,aname1,aname2,aname3):
  """
  This function calculates the order parameter for 3 atoms, it is calculated
  from the angle between the director vectors between two successive pairs of atoms.

  :param res: the residue
  :param aname1: First atom name
  :param aname2: Second atom name
  :param aname3: Third atom name

  :type res: :class:`~ost.mol.ResidueHandle`
  :type aname1: :class:`str`
  :type aname2: :class:`str`
  :type aname3: :class:`str`
  """
  a1=res.FindAtom(aname1)
  a2=res.FindAtom(aname2)
  a3=res.FindAtom(aname3)
  if not (a1.IsValid() and a2.IsValid() and a3.IsValid()):return
  v1=a1.pos-a2.pos
  v2=a2.pos-a3.pos
  return _MolecularOrderParameter(v1,v2)

def CalculateMolecularOrderParameters(res,aname_list):
  """
  This function calculates the order parameter for each successive triplet of atoms
  for a residue. The order parameter is calculated from the angle
  between the director vectors between two successive pairs of atoms.

  :param res: the residue
  :param aname_list: An ordered list of atom names. An order parameter is calculated for each successive triple of atoms

  :type res: :class:`~ost.mol.ResidueHandle`
  :type aname_list: :class:`list`
  """
  natoms=len(aname_list)
  if natoms<3:return
  return [CalculateMolecularOrderParameter(res,*aname_list[i:i+3]) for i in range(natoms-2)]

def AnalyzeMolecularOrderParameters(t,lipids,aname_list,return_average=True):
  """
  This function calculates the order parameter for each successive triplet of atoms
  for each lipid over a trajectory. The order parameter is calculated from the angle
  between the director vectors between two successive pairs of atoms.

  :param t: The trajectory
  :param lipids: Selection of the lipids to be analyzed
  :param aname_list: An ordered list of atom names. An order parameter is calculated for each successive triple of atoms
  
  :type t: :class:`~ost.mol.CoordGroupHandle`
  :type lipids: :class:`~ost.mol.EntityView`
  :type aname_list: :class:`list`
  """
  atom_triplet_list=[]
  order_parameter_list=[]
  natoms=len(aname_list)
  if natoms<3:return
  for i in range(natoms-2):
    [aname1,aname2,aname3]=aname_list[i:i+3]
    atom_triplet_list.append([aname1,aname2,aname3])
    op=FloatList()
    for res in lipids.residues:
      a1=res.FindAtom(aname1)
      a2=res.FindAtom(aname2)
      a3=res.FindAtom(aname3)
      if not (a1.IsValid() and a2.IsValid() and a3.IsValid()):
        print res,'is missing one of',aname1,aname2,aname3
        continue
      pl1=mol.alg.AnalyzeAtomPos(t,a1.handle)
      pl2=mol.alg.AnalyzeAtomPos(t,a2.handle)
      pl3=mol.alg.AnalyzeAtomPos(t,a3.handle)
      vl1=pl1-pl2
      vl2=pl2-pl3
      op.extend([_MolecularOrderParameter(v1,v2) for v1,v2 in zip(vl1,vl2)])
    order_parameter_list.append(op)
  if return_average:return atom_triplet_list,FloatList([npy.average(el) for el in order_parameter_list])
  else: return atom_triplet_list,order_parameter_list
  
  