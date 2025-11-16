import React, { useCallback, useEffect, useState } from 'react';
import {
   View,
   StyleSheet,
   TouchableOpacity,
   Text,
   Platform,
   ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';
import HomeScreen from './screens/HomeScreen';
import PeopleScreen from './screens/PeopleScreen';
import UploadScreen from './screens/UploadScreen';
import ConversationScreen from './screens/ConversationScreen';
import HighlightsScreen from './screens/HighlightsScreen';
import RetroHomeScreen from './screens/RetroHomeScreen';
import RetroPeopleScreen from './screens/RetroPeopleScreen';
import RetroUploadScreen from './screens/RetroUploadScreen';
import RetroConversationScreen from './screens/RetroConversationScreen';
import RetroHighlightsScreen from './screens/RetroHighlightsScreen';
import { retroPalette, retroFonts } from './styles/retroTheme';

const AGREEMENT_STORAGE_KEY = 'upload_agreement_accepted_v1';

export default function App() {
   const [activeTab, setActiveTab] = useState('home');
   const [activeConversation, setActiveConversation] = useState(null);
   const [hasAcceptedAgreement, setHasAcceptedAgreement] = useState(false);
   const [isCheckingAgreement, setIsCheckingAgreement] = useState(true);
   const [agreementChecked, setAgreementChecked] = useState(false);
   const [isRetroTheme, setIsRetroTheme] = useState(false);

   useEffect(() => {
      const checkAgreementStatus = async () => {
         try {
            const storedValue = await AsyncStorage.getItem(
               AGREEMENT_STORAGE_KEY
            );
            if (storedValue === 'true') {
               setHasAcceptedAgreement(true);
            }
         } catch (error) {
            console.warn('Failed to read agreement preference', error);
         } finally {
            setIsCheckingAgreement(false);
         }
      };

      checkAgreementStatus();
   }, []);

   const handleAcceptAgreement = async () => {
      try {
         await AsyncStorage.setItem(AGREEMENT_STORAGE_KEY, 'true');
         setHasAcceptedAgreement(true);
      } catch (error) {
         console.warn('Failed to save agreement acceptance', error);
      }
   };

   const handleOpenConversation = (payload) => {
      if (!payload) return;

      const normalizedPayload =
         typeof payload === 'string' ? { name: payload } : payload;
      if (!normalizedPayload || typeof normalizedPayload !== 'object') return;

      const { name, highlightTimestamp, highlightIndex, avatarUrl, headline } =
         normalizedPayload;
      if (!name) return;

      setActiveConversation({
         name,
         highlightTimestamp,
         highlightIndex,
         avatarUrl,
         headline,
      });
      setActiveTab('memory');
   };

   const handleNavigateTab = useCallback((tab) => {
      if (!tab) return;
      setActiveConversation(null);
      setActiveTab(tab);
   }, []);

   const handleToggleTheme = () => {
      setIsRetroTheme((prev) => !prev);
   };

   if (isCheckingAgreement) {
      return (
         <SafeAreaView style={{ flex: 1 }}>
            <View style={styles.agreementContainer}>
               <ActivityIndicator size='large' color='#007AFF' />
               <Text style={styles.agreementLoadingText}>Preparing app…</Text>
            </View>
         </SafeAreaView>
      );
   }

   if (!hasAcceptedAgreement) {
      return (
         <SafeAreaView style={{ flex: 1 }}>
            <View style={styles.agreementContainer}>
               <Text style={styles.agreementTitle}>Usage Agreement</Text>
               <Text style={styles.agreementCopy}>
                  To protect everyone involved, you must confirm that every
                  video uploaded through this app was recorded and shared
                  legally, with all necessary permissions.
               </Text>

               <TouchableOpacity
                  style={styles.checkboxRow}
                  onPress={() => setAgreementChecked((prev) => !prev)}
                  accessibilityRole='checkbox'
                  accessibilityState={{ checked: agreementChecked }}
               >
                  <View
                     style={[
                        styles.checkboxBase,
                        agreementChecked && styles.checkboxChecked,
                     ]}
                  >
                     {agreementChecked && (
                        <Text style={styles.checkboxMark}>✓</Text>
                     )}
                  </View>
                  <Text style={styles.checkboxLabel}>
                     I confirm every uploaded video was obtained legally and
                     with consent from all parties.
                  </Text>
               </TouchableOpacity>

               <TouchableOpacity
                  style={[
                     styles.agreeButton,
                     !agreementChecked && styles.agreeButtonDisabled,
                  ]}
                  disabled={!agreementChecked}
                  onPress={handleAcceptAgreement}
               >
                  <Text style={styles.agreeButtonText}>Agree & Continue</Text>
               </TouchableOpacity>
               <Text style={styles.agreementDisclaimer}>
                  This prompt appears only the first time you open the app.
               </Text>
            </View>
         </SafeAreaView>
      );
   }

   return (
      <SafeAreaView style={{ flex: 1 }}>
         <View style={styles.container}>
            {activeConversation ? (
               isRetroTheme ? (
                  <RetroConversationScreen
                     name={activeConversation.name}
                     avatarUrl={activeConversation.avatarUrl}
                     headline={activeConversation.headline}
                     highlightTimestamp={activeConversation.highlightTimestamp}
                     highlightIndex={activeConversation.highlightIndex}
                     onBack={() => setActiveConversation(null)}
                  />
               ) : (
                  <ConversationScreen
                     name={activeConversation.name}
                     avatarUrl={activeConversation.avatarUrl}
                     headline={activeConversation.headline}
                     highlightTimestamp={activeConversation.highlightTimestamp}
                     highlightIndex={activeConversation.highlightIndex}
                     onBack={() => setActiveConversation(null)}
                  />
               )
            ) : (
               <>
                  {activeTab === 'home' &&
                     (isRetroTheme ? (
                        <RetroHomeScreen
                           onOpenConversation={handleOpenConversation}
                           onNavigateTab={handleNavigateTab}
                        />
                     ) : (
                        <HomeScreen
                           onOpenConversation={handleOpenConversation}
                           onNavigateTab={handleNavigateTab}
                        />
                     ))}
                  {activeTab === 'upload' &&
                     (isRetroTheme ? <RetroUploadScreen /> : <UploadScreen />)}
                  {activeTab === 'memory' &&
                     (isRetroTheme ? (
                        <RetroPeopleScreen
                           onOpenConversation={handleOpenConversation}
                        />
                     ) : (
                        <PeopleScreen
                           onOpenConversation={handleOpenConversation}
                        />
                     ))}
                  {activeTab === 'highlights' &&
                     (isRetroTheme ? (
                        <RetroHighlightsScreen
                           onOpenConversation={handleOpenConversation}
                        />
                     ) : (
                        <HighlightsScreen
                           onOpenConversation={handleOpenConversation}
                        />
                     ))}
               </>
            )}

            {!activeConversation && activeTab === 'home' && (
               <TouchableOpacity
                  style={[
                     styles.themeToggleButton,
                     isRetroTheme && styles.themeToggleButtonRetro,
                  ]}
                  onPress={handleToggleTheme}
                  accessibilityRole='button'
               >
                  <Text style={styles.themeToggleText}>
                     {isRetroTheme ? 'Switch to Main' : 'Switch to Retro'}
                  </Text>
               </TouchableOpacity>
            )}

            {/* Bottom Navigation */}
            <View style={[styles.navBar, isRetroTheme && styles.navBarRetro]}>
               <TouchableOpacity
                  style={[
                     styles.navItem,
                     activeTab === 'home' && styles.navItemActive,
                     isRetroTheme && styles.navItemRetro,
                     isRetroTheme && activeTab === 'home' && styles.navItemActiveRetro,
                  ]}
                  onPress={() => {
                     setActiveConversation(null);
                     setActiveTab('home');
                  }}
               >
                  <Text
                     style={[
                        styles.navText,
                        activeTab === 'home' && styles.navTextActive,
                        isRetroTheme && styles.navTextRetro,
                        isRetroTheme && activeTab === 'home' && styles.navTextActiveRetro,
                     ]}
                  >
                     Home
                  </Text>
               </TouchableOpacity>

               <TouchableOpacity
                  style={[
                     styles.navItem,
                     styles.navSeparator,
                     activeTab === 'upload' && styles.navItemActive,
                     isRetroTheme && styles.navItemRetro,
                     isRetroTheme && styles.navSeparatorRetro,
                     isRetroTheme && activeTab === 'upload' && styles.navItemActiveRetro,
                  ]}
                  onPress={() => {
                     setActiveConversation(null);
                     setActiveTab('upload');
                  }}
               >
                  <Text
                     style={[
                        styles.navText,
                        activeTab === 'upload' && styles.navTextActive,
                        isRetroTheme && styles.navTextRetro,
                        isRetroTheme && activeTab === 'upload' && styles.navTextActiveRetro,
                     ]}
                  >
                     Upload
                  </Text>
               </TouchableOpacity>

               <TouchableOpacity
                  style={[
                     styles.navItem,
                     styles.navSeparator,
                     activeTab === 'highlights' && styles.navItemActive,
                     isRetroTheme && styles.navItemRetro,
                     isRetroTheme && styles.navSeparatorRetro,
                     isRetroTheme && activeTab === 'highlights' && styles.navItemActiveRetro,
                  ]}
                  onPress={() => {
                     setActiveConversation(null);
                     setActiveTab('highlights');
                  }}
               >
                  <Text
                     style={[
                        styles.navText,
                        activeTab === 'highlights' && styles.navTextActive,
                        isRetroTheme && styles.navTextRetro,
                        isRetroTheme && activeTab === 'highlights' && styles.navTextActiveRetro,
                     ]}
                  >
                     Highlights
                  </Text>
               </TouchableOpacity>

               <TouchableOpacity
                  style={[
                     styles.navItem,
                     styles.navSeparator,
                     activeTab === 'memory' && styles.navItemActive,
                     isRetroTheme && styles.navItemRetro,
                     isRetroTheme && styles.navSeparatorRetro,
                     isRetroTheme && activeTab === 'memory' && styles.navItemActiveRetro,
                  ]}
                  onPress={() => {
                     setActiveConversation(null);
                     setActiveTab('memory');
                  }}
               >
                  <Text
                     style={[
                        styles.navText,
                        activeTab === 'memory' && styles.navTextActive,
                        isRetroTheme && styles.navTextRetro,
                        isRetroTheme && activeTab === 'memory' && styles.navTextActiveRetro,
                     ]}
                  >
                     Memory
                  </Text>
               </TouchableOpacity>
            </View>
         </View>
      </SafeAreaView>
   );
}

const styles = StyleSheet.create({
   container: {
      flex: 1,
      backgroundColor: '#fff',
   },
   agreementContainer: {
      flex: 1,
      paddingHorizontal: 24,
      justifyContent: 'center',
      backgroundColor: '#fff',
   },
   agreementTitle: {
      fontSize: 24,
      fontWeight: '700',
      marginBottom: 16,
      textAlign: 'center',
      color: '#111',
   },
   agreementCopy: {
      fontSize: 16,
      color: '#333',
      marginBottom: 24,
      lineHeight: 22,
      textAlign: 'center',
   },
   checkboxRow: {
      flexDirection: 'row',
      alignItems: 'center',
      marginBottom: 24,
   },
   checkboxBase: {
      width: 28,
      height: 28,
      borderWidth: 2,
      borderColor: '#007AFF',
      borderRadius: 6,
      marginRight: 12,
      alignItems: 'center',
      justifyContent: 'center',
   },
   checkboxChecked: {
      backgroundColor: '#007AFF',
   },
   checkboxMark: {
      color: '#fff',
      fontSize: 18,
      fontWeight: '700',
   },
   checkboxLabel: {
      flex: 1,
      fontSize: 15,
      color: '#222',
      lineHeight: 20,
   },
   agreeButton: {
      backgroundColor: '#007AFF',
      paddingVertical: 16,
      borderRadius: 12,
      alignItems: 'center',
   },
   agreeButtonDisabled: {
      backgroundColor: '#89bfff',
   },
   agreeButtonText: {
      color: '#fff',
      fontSize: 16,
      fontWeight: '600',
   },
   agreementDisclaimer: {
      marginTop: 16,
      textAlign: 'center',
      color: '#666',
      fontSize: 13,
   },
   agreementLoadingText: {
      marginTop: 12,
      fontSize: 16,
      color: '#555',
      textAlign: 'center',
   },
   navBar: {
      flexDirection: 'row',
      borderTopWidth: 1,
      borderTopColor: '#ddd',
      backgroundColor: '#fff',
      height: 64,
      alignItems: 'center',
   },
   navItem: {
      flex: 1,
      paddingVertical: 16,
      alignItems: 'center',
      justifyContent: 'center',
   },
   navSeparator: {
      borderLeftWidth: 1,
      borderLeftColor: '#eee',
   },
   navItemActive: {
      borderTopWidth: 3,
      borderTopColor: '#007AFF',
   },
   navText: {
      fontSize: 14,
      color: '#000',
      fontFamily:
         Platform.OS === 'ios'
            ? 'American Typewriter'
            : Platform.OS === 'android'
            ? 'monospace'
            : 'Courier New',
      fontWeight: '700',
      textTransform: 'uppercase',
   },
   navTextActive: {
      color: '#007AFF',
      fontWeight: '600',
   },
   navBarRetro: {
      backgroundColor: retroPalette.menuGray,
      borderTopWidth: 3,
      borderTopColor: retroPalette.outline,
      height: 70,
   },
   navItemRetro: {
      backgroundColor: retroPalette.menuGray,
   },
   navSeparatorRetro: {
      borderLeftWidth: 2,
      borderLeftColor: retroPalette.outline,
   },
   navItemActiveRetro: {
      backgroundColor: retroPalette.warmSand,
      borderTopWidth: 4,
      borderTopColor: retroPalette.violet,
   },
   navTextRetro: {
      fontFamily: retroFonts.base,
      color: retroPalette.menuText,
      fontSize: 15,
   },
   navTextActiveRetro: {
      color: retroPalette.violet,
      fontWeight: '700',
   },
   themeToggleButton: {
      marginTop: 32,
      position: 'absolute',
      top: 16,
      right: 16,
      paddingVertical: 10,
      paddingHorizontal: 16,
      borderRadius: 20,
      backgroundColor: '#111',
      zIndex: 10,
   },
   themeToggleButtonRetro: {
      marginTop: 32,
      backgroundColor: '#f6b352',
   },
   themeToggleText: {
      color: '#fff',
      fontWeight: '700',
      textTransform: 'uppercase',
      fontSize: 12,
   },
});
