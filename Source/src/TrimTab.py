import os
import numpy as np
from tkinter import ttk, StringVar, Frame, Label, Button, Entry, messagebox
from tkinter.messagebox import askyesno
from settings import TEMP_PATH, COLORS
from .Global_Functions import isNumber, findClosest

class TrimTab(Frame):
    ''' Contains all variables and widgets of the Trim Spectra Tab '''
    def __init__(self, notebook: ttk.Notebook):
        super().__init__(notebook)
        self.notebook = notebook
        self.window = notebook.window

        self.varTrimFixed_value = StringVar(value = '')
        self.varTrimHigh_value = StringVar(value = '')
        self.varTrimLow_value = StringVar(value = '')
        
        self.allChangesSaved = True
        self.configureLayout()
        
        self.varTrimFixed_value.trace('w', self.changeMade)
        self.varTrimHigh_value.trace('w', self.changeMade)
        self.varTrimLow_value.trace('w', self.changeMade)

    def changeMade(self, name, index, trigger):
        ''' Triggered everytime an input variable is changed '''
        self.allChangesSaved = False

    def clearTab(self):
        ''' Reinitialize tab '''
        self.varTrimFixed_value.set('')
        self.varTrimHigh_value.set('')
        self.varTrimLow_value.set('')
        self.allChangesSaved = True

    def discardChanges(self):
        ''' Upon a tab change, checks for unsaved changes. '''
        if self.allChangesSaved:
            return True
        
        if askyesno('Warning', 'Discard unsaved Trim settings?'):
            self.clearTab()
            return True
        else:
            return False

    def handleMouseEvent(self, x: float, y: float):
        ''' Placeholder to avoid crashes on mouse clicks in the plot '''
        pass

    def configureLayout(self):
        ''' Configures the tab layout '''
        Label(self, text = 'Fixed Value: ').grid(column = 0, row = 2, sticky = 'E')
        Label(self, text = 'High Value ').grid(column = 0, row = 3, sticky = 'E')
        Label(self, text = 'Low Value ').grid(column = 0, row = 4, sticky = 'E')
        
        self.TrimFixed_value = Entry(self, textvariable = self.varTrimFixed_value, validate = 'all', 
                             validatecommand = (self.register(isNumber), '%P'))
        self.TrimFixed_value.grid(column = 1, row = 2, sticky = 'W')
        
        self.TrimHigh_value = Entry(self, textvariable = self.varTrimHigh_value, validate = 'all', 
                             validatecommand = (self.register(isNumber), '%P'))
        self.TrimHigh_value.grid(column = 1, row = 3, sticky = 'W')
        
        self.TrimLow_value = Entry(self, textvariable = self.varTrimLow_value, validate = 'all', 
                             validatecommand = (self.register(isNumber), '%P'))
        self.TrimLow_value.grid(column = 1, row = 4, sticky = 'W')    

        self.btnPerformTrim = Button(self, text='Perform Trim', command=self.PerformAvgTrimSpectra)
        self.btnPerformTrim.grid(column=0, row=0, sticky='w')

        self.btnSaveTrim = Button(self, text='Save Trim', command=self.SaveAvgTrimSpectra)
        self.btnSaveTrim.grid(column=1, row=0, sticky='w')

    def getValue(self, file_path, fixed_value):
        ''' Extrae el valor Z real asociado al X más cercano al FixedValue '''
        x_values = []
        z_values_dict = {}
        
        with open(file_path, 'r') as file:
            next(file)
            for line in file:
                values = line.strip().split()
                if len(values) >= 4:
                    x = float(values[0])
                    y = float(values[1])
                    y0 = float(values[3])
                    z = y - y0
                    
                    x_values.append(x)
                    z_values_dict[x] = z
        
        if not x_values:
            return None
            
        closest_index = findClosest(fixed_value, x_values)
        closest_actual_x = x_values[closest_index]
        return z_values_dict[closest_actual_x]

    def trim_function(self, fixed_value, high_trim, low_trim):
        ''' Core mathematical function to filter and average spectra '''
        if self.window.maps.isEmpty(): return 1

        # Calculate step size for progress bar update (assuming 1 step per map)
        progressStep = 100 / self.window.maps.length() if self.window.maps.length() > 0 else 100
        self.window.statFrame.progressLabel.config(text='Processing: Trimming spectra...')
        self.window.statFrame.progressBar['value'] = 0

        for map in self.window.maps:
            value_data = np.array([])
            spectra_files = []
            x_values = []
            
            fit_dir = f'{map.directory}/{map.orig}_Files/Fits'
            
            if not os.path.exists(fit_dir): 
                messagebox.showwarning("Warning", f"No Fits directory found for map {map.name}")
                continue

            for file in os.listdir(fit_dir):
                if file.endswith('.txt'):
                    file_path = os.path.join(fit_dir, file)
                    value = self.getValue(file_path, fixed_value)
                    
                    if value is not None:
                        value_data = np.append(value_data, [value])
                        sorted_value_data = np.sort(value_data)[::-1]
                        num_discard_higher = int((len(value_data)) * high_trim)
                        num_discard_lower = int((len(value_data)) * low_trim)
                        
                        if num_discard_lower == 0:
                            trimmed_data = sorted_value_data[num_discard_higher:]
                        else:
                            trimmed_data = sorted_value_data[num_discard_higher:-num_discard_lower]
                        
                        if value in trimmed_data:
                            spectra_files.append(file_path)

            if spectra_files:
                x_file = spectra_files[0]
                with open(x_file, 'r') as file:
                    next(file)
                    for line in file:
                        values = line.strip().split()
                        if len(values) >= 2:
                            x = float(values[0])  
                            x_values.append(x)
                    
                y_sum = [0]*len(x_values)
                
                for file in spectra_files:
                    y_vals = []
                    with open(file, 'r') as f:
                        next(f)
                        for line in f:
                            vals = line.strip().split()
                            if len(vals) >= 2:
                                y_vals.append(float(vals[1]))
                    
                    min_len = min(len(y_sum), len(y_vals))
                    y_sum = y_sum[:min_len]
                    y_vals = y_vals[:min_len]
                    x_values = x_values[:min_len] 
                    
                    y_sum = list(np.add(y_sum, y_vals))
                    
                w = len(spectra_files)
                y_avg = [y / w for y in y_sum]
                
                filename = os.path.join(TEMP_PATH, f'{map.orig}_avgtrimmed.txt')
            
                with open(filename, 'w') as f:
                    f.write('Wavenumber(cm-1)\tIntensity\n')
                    for x, avg in zip(x_values, y_avg):
                        f.write(f"{x:.2f}\t{avg:.2f}\n")
            
            # Update progress bar per map processed
            self.window.statFrame.progressBar['value'] += progressStep
            self.window.statFrame.update_idletasks()

        # Reset progress bar UI
        self.window.statFrame.progressBar['value'] = 0
        self.window.statFrame.progressLabel.config(text='Processing: ')

    def PerformAvgTrimSpectra(self):
        ''' Parses input and calls the trim function '''
        if not self.varTrimFixed_value.get() or not self.varTrimHigh_value.get() or not self.varTrimLow_value.get():
            messagebox.showwarning("Warning", "Please fill in all value fields.")
            return 1

        try:
            fixed_value = float(self.varTrimFixed_value.get())
            high_value = float(self.varTrimHigh_value.get())
            low_value = float(self.varTrimLow_value.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numeric values.")
            return 1
            
        self.trim_function(fixed_value, high_value, low_value)
        
        self.window.statFrame.logText.config(state='normal')
        self.window.statFrame.logText.insert('end', f"\n> Trim calculated at Fixed Value: {fixed_value}")
        self.window.statFrame.logText.see('end')
        self.window.statFrame.logText.config(state='disabled')
        
        self.displaySpectra()
        
        return 0

    def SaveAvgTrimSpectra(self):
        ''' Exports the temp trimmed files into the source directory '''
        if self.window.maps.isEmpty(): return 1
        
        saved_files = 0
        for map in self.window.maps:
            os.chdir(map.directory)
            TEMP_File = os.path.join(TEMP_PATH, f'{map.orig}_avgtrimmed.txt')
            
            if os.path.exists(TEMP_File):
                with open(f'{map.orig}_avgstrimspectra.txt', 'wt') as avg_file:
                    with open(TEMP_File, 'r') as file:
                        for line in file:
                            avg_file.write(line)
                saved_files += 1
        
        if saved_files > 0:

            try:
                self.window.insertLog('trim')
            except Exception:

                self.window.statFrame.logText.config(state='normal')
                self.window.statFrame.logText.insert('end', f"\n> {saved_files} trimmed maps saved")
                self.window.statFrame.logText.see('end')
                self.window.statFrame.logText.config(state='disabled')
            
            messagebox.showinfo("Save", "Trimmed spectra saved successfully in original directory.")
            self.allChangesSaved = True
        else:
            messagebox.showwarning("Warning", "No trimmed data found. Please perform trim first.")
            
        os.chdir(TEMP_PATH)
        return 0

    def displaySpectra(self, window = None):
        ''' Displays trimmed spectra if available, otherwise shows normal average. '''
        if window is None:
            window = self.window
            
        if window.maps.isEmpty():
            return 1
        
        plot = window.plotFrame.figure.reInitPlot()
        
        trimmed_data_found = False
        
        for col, map in enumerate(window.maps):
            temp_file = os.path.join(TEMP_PATH, f'{map.orig}_avgtrimmed.txt')
            if os.path.exists(temp_file):
                x_vals = []
                y_vals = []
                with open(temp_file, 'r') as f:
                    next(f)
                    for line in f:
                        vals = line.strip().split()
                        if len(vals) >= 2:
                            x_vals.append(float(vals[0]))
                            y_vals.append(float(vals[1]))
                
                if x_vals:
                    plot.plot(x_vals, y_vals, color=COLORS[col % len(COLORS)], label=map.name)
                    trimmed_data_found = True
        
        if not trimmed_data_found:
            window.getAverageSpectra()
            for col, spectra in window.averages.enumerate():  
                plot.plot(spectra[1][0], spectra[1][1], color=COLORS[col % len(COLORS)])
        

        try:
            if self.varTrimFixed_value.get():
                fixed = float(self.varTrimFixed_value.get())
                plot.axvline(x=fixed, color='gray', linestyle='--')
        except ValueError:
            pass

        window.plotFrame.figure.saveLimits()
        window.plotFrame.figure.drawCanvas()
        self.window.statFrame.getLimits()