<?xml version='1.0' encoding='UTF-8'?>
<Element xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="https://pythonparts.allplan.com/2026/schemas/PythonPart.xsd">
  <Script>
    <Name>ReinforcementExamples\SeismicColumn\SeismicColumn.py</Name>
    <Title>Stâlp armat EC2 + P100-1</Title>
    <Version>1.0</Version>
    <ReadLastInput>True</ReadLastInput>
  </Script>
  <Page>
    <Name>Geometry</Name>
    <Text>Geometrie</Text>
    <Parameters>
      <Parameter>
        <Name>Width</Name>
        <Text>Latura b (X)</Text>
        <Value>600.</Value>
        <MinValue>200.</MinValue>
        <ValueType>Length</ValueType>
      </Parameter>
      <Parameter>
        <Name>Depth</Name>
        <Text>Latura h (Y)</Text>
        <Value>600.</Value>
        <MinValue>200.</MinValue>
        <ValueType>Length</ValueType>
      </Parameter>
      <Parameter>
        <Name>Height</Name>
        <Text>Înălțimea liberă lcl</Text>
        <Value>3000.</Value>
        <MinValue>500.</MinValue>
        <ValueType>Length</ValueType>
      </Parameter>
      <Parameter>
        <Name>ConcreteCover</Name>
        <Text>Acoperire nominală (la etrier)</Text>
        <Value>30.</Value>
        <ValueType>ReinfConcreteCover</ValueType>
      </Parameter>
      <Parameter>
        <Name>BucklingFactor</Name>
        <Text>Coeficient lungime de flambaj l0/lcl</Text>
        <Value>1.0</Value>
        <MinValue>0.5</MinValue>
        <MaxValue>3.0</MaxValue>
        <ValueType>Double</ValueType>
      </Parameter>
    </Parameters>
  </Page>
  <Page>
    <Name>Design</Name>
    <Text>Materiale și normativ</Text>
    <Parameters>
      <Parameter>
        <Name>DesignExpander</Name>
        <Text>Calcul (EC2 + P100-1/2013)</Text>
        <ValueType>Expander</ValueType>
        <Parameters>
          <Parameter>
            <Name>ConcreteClass</Name>
            <Text>Clasa betonului</Text>
            <Value>C30/37</Value>
            <ValueList>C16/20|C20/25|C25/30|C30/37|C35/45|C40/50|C45/55|C50/60</ValueList>
            <ValueType>StringComboBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>SteelFyk</Name>
            <Text>fyk oțel [MPa]</Text>
            <Value>500.</Value>
            <MinValue>200.</MinValue>
            <MaxValue>600.</MaxValue>
            <ValueType>Double</ValueType>
          </Parameter>
          <Parameter>
            <Name>DuctilityClass</Name>
            <Text>Clasa de ductilitate</Text>
            <Value>DCH</Value>
            <ValueList>DCH|DCM</ValueList>
            <ValueType>StringComboBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>IsBaseColumn</Name>
            <Text>Stâlp la baza clădirii</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>BeamColumnRatio</Name>
            <Text>ΣMRb / ΣMRc (calcul la capacitate V)</Text>
            <Value>1.0</Value>
            <MinValue>0.0</MinValue>
            <MaxValue>1.0</MaxValue>
            <ValueType>Double</ValueType>
          </Parameter>
          <Parameter>
            <Name>MaxAggregate</Name>
            <Text>Dimensiunea maximă a agregatului dg</Text>
            <Value>16.</Value>
            <ValueType>Length</ValueType>
          </Parameter>
        </Parameters>
      </Parameter>
      <Parameter>
        <Name>AllplanExpander</Name>
        <Text>Proprietăți armătură Allplan</Text>
        <ValueType>Expander</ValueType>
        <Parameters>
          <Parameter>
            <Name>SteelGrade</Name>
            <Text>Marca oțelului</Text>
            <Value>-1</Value>
            <ValueType>ReinfSteelGrade</ValueType>
          </Parameter>
          <Parameter>
            <Name>ConcreteGrade</Name>
            <Text>Clasa betonului (Allplan)</Text>
            <Value>-1</Value>
            <ValueType>ReinfConcreteGrade</ValueType>
          </Parameter>
          <Parameter>
            <Name>CreateReinforcement</Name>
            <Text>Creează armătura</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
          <Parameter>
            <Name>StarterBars</Name>
            <Text>Prelungește barele cu lungimea de suprapunere</Text>
            <Value>True</Value>
            <ValueType>CheckBox</ValueType>
          </Parameter>
        </Parameters>
      </Parameter>
    </Parameters>
  </Page>
  <Page>
    <Name>Efforts</Name>
    <Text>Eforturi</Text>
    <Parameters>
      <Parameter>
        <Name>EffortsFile</Name>
        <Text>Fișier eforturi (gol = exemplu)</Text>
        <Value/>
        <ValueType>String</ValueType>
        <ValueDialog>OpenFileDialog</ValueDialog>
        <FileFilter>csv-files(*.csv)|*.csv|txt-files(*.txt)|*.txt|</FileFilter>
        <FileExtension>csv</FileExtension>
        <DefaultDirectories>etc|std|usr|prj</DefaultDirectories>
      </Parameter>
      <Parameter>
        <Name>ColumnId</Name>
        <Text>Stâlp (coloana Stalp, gol = toate rândurile)</Text>
        <Value>S1</Value>
        <ValueType>String</ValueType>
      </Parameter>
      <Parameter>
        <Name>WriteReport</Name>
        <Text>Scrie raportul de calcul lângă fișier</Text>
        <Value>True</Value>
        <ValueType>CheckBox</ValueType>
      </Parameter>
    </Parameters>
  </Page>
</Element>
