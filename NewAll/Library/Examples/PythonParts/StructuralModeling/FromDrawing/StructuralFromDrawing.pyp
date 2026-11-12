<?xml version='1.0' encoding='UTF-8'?>
<Element xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="https://pythonparts.allplan.com/2026/schemas/PythonPart.xsd">
  <Script>
    <Name>StructuralModeling\FromDrawing\StructuralFromDrawing.py</Name>
    <Title>Structură din planșă</Title>
    <Version>1.0</Version>
    <Interactor>True</Interactor>
    <ReadLastInput>True</ReadLastInput>
  </Script>
  <Page>
    <Name>Input</Name>
    <Text>Planșă și etaj</Text>
    <Parameters>
      <Parameter>
        <Name>SourceExpander</Name>
        <Text>Sursa planșei</Text>
        <ValueType>Expander</ValueType>
        <Parameters>
          <Parameter>
            <Name>Source</Name>
            <Text>Sursa</Text>
            <Value>1</Value>
            <ValueType>RadioButtonGroup</ValueType>
            <Parameters>
              <Parameter>
                <Name>SourceModel</Name>
                <Text>Selecție din model</Text>
                <Value>1</Value>
                <ValueType>RadioButton</ValueType>
              </Parameter>
              <Parameter>
                <Name>SourceDxf</Name>
                <Text>Fișier DXF</Text>
                <Value>2</Value>
                <ValueType>RadioButton</ValueType>
              </Parameter>
            </Parameters>
          </Parameter>
          <Parameter>
            <Name>DxfFile</Name>
            <Text>Fișier DXF</Text>
            <Value/>
            <ValueType>String</ValueType>
            <ValueDialog>OpenFileDialog</ValueDialog>
            <FileFilter>dxf-files(*.dxf)|*.dxf|</FileFilter>
            <FileExtension>dxf</FileExtension>
            <DefaultDirectories>etc|std|usr|prj</DefaultDirectories>
            <Visible>Source == 2</Visible>
          </Parameter>
          <Parameter>
            <Name>RulesFile</Name>
            <Text>Fișier reguli (gol = implicit)</Text>
            <Value/>
            <ValueType>String</ValueType>
            <ValueDialog>OpenFileDialog</ValueDialog>
            <FileFilter>json-files(*.json)|*.json|</FileFilter>
            <FileExtension>json</FileExtension>
            <DefaultDirectories>etc|std|usr|prj</DefaultDirectories>
          </Parameter>
        </Parameters>
      </Parameter>
      <Parameter>
        <Name>LevelExpander</Name>
        <Text>Etaj</Text>
        <ValueType>Expander</ValueType>
        <Parameters>
          <Parameter>
            <Name>LevelName</Name>
            <Text>Nume etaj</Text>
            <Value>Parter</Value>
            <ValueType>String</ValueType>
          </Parameter>
          <Parameter>
            <Name>LevelBottom</Name>
            <Text>Cotă jos</Text>
            <Value>0.</Value>
            <ValueType>Length</ValueType>
          </Parameter>
          <Parameter>
            <Name>StoreyHeight</Name>
            <Text>Înălțime etaj</Text>
            <Value>3000.</Value>
            <MinValue>100.</MinValue>
            <ValueType>Length</ValueType>
          </Parameter>
        </Parameters>
      </Parameter>
      <Parameter>
        <Name>OverrideExpander</Name>
        <Text>Suprascrieri (0 = valoarea din reguli)</Text>
        <ValueType>Expander</ValueType>
        <Parameters>
          <Parameter>
            <Name>BeamWidth</Name>
            <Text>Lățime grindă</Text>
            <Value>0.</Value>
            <MinValue>0.</MinValue>
            <ValueType>Length</ValueType>
          </Parameter>
          <Parameter>
            <Name>BeamDepth</Name>
            <Text>Înălțime grindă</Text>
            <Value>0.</Value>
            <MinValue>0.</MinValue>
            <ValueType>Length</ValueType>
          </Parameter>
          <Parameter>
            <Name>SlabThickness</Name>
            <Text>Grosime placă</Text>
            <Value>0.</Value>
            <MinValue>0.</MinValue>
            <ValueType>Length</ValueType>
          </Parameter>
        </Parameters>
      </Parameter>
      <Parameter>
        <Name>TypesExpander</Name>
        <Text>Elemente create</Text>
        <ValueType>Expander</ValueType>
        <Parameters>
          <Parameter>
            <Name>CreateColumns</Name>
            <Text>Stâlpi</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>CreateWalls</Name>
            <Text>Pereți</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>CreateBeams</Name>
            <Text>Grinzi</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>CreateSlabs</Name>
            <Text>Plăci</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
        </Parameters>
      </Parameter>
      <Parameter>
        <Name>CreateButtonRow</Name>
        <Text>Recunoaștere</Text>
        <ValueType>Row</ValueType>
        <Parameters>
          <Parameter>
            <Name>CreateButton</Name>
            <Text>Recunoaște și creează</Text>
            <EventId>1001</EventId>
            <ValueType>Button</ValueType>
          </Parameter>
        </Parameters>
      </Parameter>
    </Parameters>
  </Page>
</Element>
