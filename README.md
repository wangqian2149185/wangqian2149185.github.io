# Wymol

Wymol is an interactive, browser-based protein interaction atlas and PDB structure viewer. It helps learners and researchers build intuition for the physical forces that stabilize protein structures and inspect atom-level interactions directly from PDB coordinates.

Wymol runs as a single HTML page. No installation or server is required for the built-in learning modules. English is shown by default, with Chinese available from the language switch.

## Features

### Interaction atlas

- Explains five underlying physical origins: electrostatics, dispersion/van der Waals forces, polarization, charge transfer, and solvent/entropy effects.
- Places common protein interactions on a logarithmic energy scale.
- Covers hydrogen bonds, salt bridges, cation–π and π–π interactions, CH–π and S–π contacts, disulfide bonds, metal coordination, hydrophobic contacts, halogen bonds, water bridges, and n→π* interactions.
- Shows the atoms or functional groups involved, common residues, approximate energy ranges, and geometry notes.
- Filters interactions by strength, biological system, and dominant physical origin.

### Amino-acid explorer

- Browse all standard amino acids.
- Select a residue to see the interactions it can form and the structural roles it commonly plays.
- Open detailed explanations for each linked interaction type.

### PDB interaction viewer

- Load a local `.pdb`, `.ent`, or text-format PDB file by clicking or dragging it into the page.
- Fetch a structure by entering a four-character PDB ID.
- Start quickly with the included example structures.
- Detect atom-level interactions from distance and angle rules directly in the browser.
- Visualize detected contacts on a 3D structure with lines or directional arrows.
- Select one or multiple residues, search by residue name or number, and inspect their interaction lists.
- Toggle residue labels and water molecules.
- Estimate interaction energies and report interaction occupancy for multi-model structures such as NMR ensembles.
- Display hydrophobic burial as a surface-based effect rather than a fictitious “hydrophobic bond.”

## How to use Wymol

### Open the application

Open [`pages/chemistry/Wymol.html`](pages/chemistry/Wymol.html) in a modern desktop browser, or use the published version:

<https://wangqian2149185.github.io/pages/chemistry/Wymol.html>

The learning atlas works directly from the HTML file. Internet access is needed when fetching a PDB ID and when loading the 3Dmol.js viewer.

### Explore the interaction reference

1. Read **The five physical origins** to understand the components behind named interactions.
2. Use the energy-scale chart to compare typical interaction magnitudes.
3. Filter the interaction cards by strength, system, or physical origin.
4. Click a card to open its detailed explanation, geometry, and energy information.
5. Select an amino acid in **By amino acid** to review the interactions available to that residue.

### Analyze a protein structure

1. Scroll to **Upload PDB · structural interaction viewer**.
2. Choose one input method:
   - Drag a local PDB file into the upload area.
   - Click the upload area and select a file.
   - Enter a PDB ID and select **Fetch**.
   - Choose one of the example structures.
3. Wait for Wymol to parse the coordinates and detect interactions.
4. Click a residue in the 3D viewer or residue list.
5. Review its atom-level contacts, distances, directions, estimated energies, and occupancy values.
6. Hold `Ctrl` on Windows/Linux or `⌘` on macOS while clicking to select multiple residues.
7. Use **Residue labels** and **Water** to adjust the structural view.

## Interpretation notes

- Reported energies are approximate interaction energies for teaching and exploration; they are not rigorous binding or folding free energies (`ΔG`).
- Geometry-based detection depends on the quality, protonation state, alternate conformations, missing atoms, and resolution of the input structure.
- Occupancy from a multi-model PDB describes how often a geometry is detected across the supplied models. It is not a molecular-dynamics probability unless the models come from an appropriate ensemble.
- Hydrophobic stabilization is a solvent-driven free-energy effect. Wymol separates it conceptually from direct dispersion and steric contacts.
- Quantitative conclusions should be validated with experimental evidence or appropriate molecular simulation and quantum-chemistry methods.

## Privacy

Local files are parsed in the browser. Wymol does not upload local PDB files to an application server. Fetching a PDB ID sends a request to the public RCSB PDB file service, and the 3D viewer library is loaded from a public CDN.

## Browser support

Use a current version of Chrome, Edge, Firefox, or Safari. A desktop browser is recommended for the 3D viewer and dense interaction panels.
